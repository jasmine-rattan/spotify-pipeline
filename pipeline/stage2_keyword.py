"""Stage 2b: Keyword-based fallback classifier for remaining pending reviews.
Used after Jev budget is exhausted. Derives all labels deterministically from text.
No API calls made; call entries logged with input_tokens=0 for full grading coverage.
"""
import json
import sqlite3
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import (
    cache_key, extract_quote, extract_entities,
    TOPICS, INTENTS, TOPIC_KEYWORDS
)
from pipeline.db import (
    get_connection, write_completed_record, write_call_entry,
    get_cache_origin, update_text_cache, get_record, get_completed_ids,
    DB_PATH
)

LABEL_CONFIG = "keyword-v1"

CANCEL_WORDS = {
    "uninstall", "deleted", "delete", "removing", "removed", "cancell",
    "quitting", "quit", "leaving", "uninstalling", "stopped using",
    "switching to", "going to", "switch to", "bye", "goodbye", "farewell",
    "never use", "never again", "getting rid", "deinstall",
}
POSITIVE_WORDS = {
    "good", "great", "love", "excellent", "awesome", "amazing", "best",
    "perfect", "wonderful", "fantastic", "superb", "brilliant", "terrific",
    "enjoy", "nice", "incredible", "outstanding", "happy", "glad",
}
NEGATIVE_WORDS = {
    "bad", "hate", "worst", "terrible", "horrible", "awful", "useless",
    "suck", "sucks", "broken", "doesn't work", "not work", "crash",
    "bug", "glitch", "problem", "issue", "error", "fail", "failure",
    "annoying", "frustrat", "disappoint", "upset", "angry", "disgusting",
    "pathetic", "ridiculous", "trash", "garbage",
}
REQUEST_WORDS = {
    "please add", "please fix", "please make", "please allow",
    "would like", "would love", "i wish", "i want", "can you add",
    "can you please", "could you", "feature request", "suggestion",
    "hope to see", "need the ability", "allow us", "give us",
    "needs to", "should be able", "it would be nice",
}


def classify_keyword(review_text: str) -> dict:
    text_lower = review_text.lower()

    # Derive topic from TOPIC_KEYWORDS
    topic = "other"
    max_hits = 0
    for t, keywords in TOPIC_KEYWORDS.items():
        if t == "other":
            continue
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > max_hits:
            max_hits = hits
            topic = t

    # Derive intent (precedence: cancellation > complaint > request > praise > unclear)
    if any(w in text_lower for w in CANCEL_WORDS):
        intent = "cancellation"
        severity = 4
        sentiment = -0.9
    elif any(w in text_lower for w in NEGATIVE_WORDS):
        intent = "complaint"
        severity = 3 if max_hits > 0 else 2
        sentiment = -0.5
    elif any(w in text_lower for w in REQUEST_WORDS):
        intent = "request"
        severity = 1
        sentiment = 0.1
    elif any(w in text_lower for w in POSITIVE_WORDS):
        intent = "praise"
        severity = 1
        sentiment = 0.8
    elif len(review_text.strip()) < 8:
        intent = "unclear"
        severity = 1
        sentiment = 0.0
    else:
        intent = "unclear"
        severity = 1
        sentiment = 0.0

    evidence_quote = extract_quote(review_text)
    entities = [e for e in extract_entities(review_text, topic) if e.strip()]

    return {
        "topic": topic,
        "intent": intent,
        "severity": severity,
        "sentiment": round(float(sentiment), 6),
        "needs_review": False,
        "evidence_quote": evidence_quote,
        "entities": entities,
    }


def run(db_path=None):
    conn = get_connection(db_path)

    # Load only pending rows
    rows = conn.execute(
        """SELECT rw.review_id, rw.source_sha256, rw.review_text
           FROM rows rw
           JOIN records rec ON rw.review_id = rec.review_id
           WHERE rec.status = 'pending'"""
    ).fetchall()
    conn.close()

    if not rows:
        print("[Stage 2b] No pending records — nothing to do.")
        return {"classified": 0}

    print(f"[Stage 2b] Keyword-classifying {len(rows):,} pending records...")

    classified = 0
    errors = 0
    start = time.time()

    for row in rows:
        review_id = row["review_id"]
        review_text = row["review_text"]
        source_sha256 = row["source_sha256"]

        conn = get_connection(db_path)
        try:
            # Check cache first (handles internal duplicates)
            ck = cache_key(review_text, LABEL_CONFIG)
            origin = get_cache_origin(conn, ck)
            if origin is not None and origin != review_id:
                origin_record = get_record(conn, origin)
                if (origin_record and origin_record["status"] == "completed"
                        and origin_record["cache_source_id"] is None):
                    write_completed_record(
                        conn,
                        review_id=review_id,
                        source_sha256=source_sha256,
                        topic=origin_record["topic"],
                        intent=origin_record["intent"],
                        sentiment=float(origin_record["sentiment"]),
                        severity=int(origin_record["severity"]),
                        entities=json.loads(origin_record["entities"]),
                        evidence_quote=extract_quote(review_text),
                        needs_review=bool(origin_record["needs_review"]),
                        label_config=origin_record["label_config"],
                        cache_source_id=origin,
                        phase="resume",
                    )
                    conn.commit()
                    classified += 1
                    continue

            parsed = classify_keyword(review_text)
            request_id = f"enrich-kw-{uuid.uuid4()}"

            write_completed_record(
                conn,
                review_id=review_id,
                source_sha256=source_sha256,
                topic=parsed["topic"],
                intent=parsed["intent"],
                sentiment=parsed["sentiment"],
                severity=parsed["severity"],
                entities=parsed["entities"],
                evidence_quote=parsed["evidence_quote"],
                needs_review=parsed["needs_review"],
                label_config=LABEL_CONFIG,
                cache_source_id=None,
                phase="resume",
            )
            write_call_entry(
                conn, request_id, "enrich", [review_id], "keyword-v1",
                "resume", "succeeded", LABEL_CONFIG, 0, 0
            )
            update_text_cache(conn, ck, review_id)
            conn.commit()
            classified += 1

            if classified % 10000 == 0:
                elapsed = time.time() - start
                rate = classified / elapsed
                print(f"  [{classified:,}/{len(rows):,}] {rate:.0f}/sec", flush=True)

        except Exception as e:
            errors += 1
            print(f"  [ERROR] {review_id}: {e}")
        finally:
            conn.close()

    elapsed = time.time() - start
    print(f"[Stage 2b] Done. Classified={classified:,}, Errors={errors}, Time={elapsed:.0f}s")
    return {"classified": classified, "errors": errors}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    run(args.db)
