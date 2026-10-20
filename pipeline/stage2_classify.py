"""Stage 2: Classify reviews using Jev (TypeSafe). Cache deduplication + checkpoints.
Concurrent requests via ThreadPoolExecutor for throughput.
"""
import json
import math
import os
import sqlite3
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import (
    cache_key, extract_quote, extract_entities,
    TOPICS, INTENTS, TOPIC_KEYWORDS
)

# v3: ask Jev for intent only (~318 tokens avg, $4.48 for 335K reviews).
# topic derived from TOPIC_KEYWORDS; severity/sentiment derived from intent.
# label_config distinguishes these records from the v1 full-question records.
LABEL_CONFIG = "jev-1.14.0+classify-v3"

INTENT_TO_SEVERITY = {
    "cancellation": 4,
    "complaint": 3,
    "request": 1,
    "praise": 1,
    "unclear": 1,
}

INTENT_TO_SENTIMENT = {
    "cancellation": -0.9,
    "complaint": -0.5,
    "request": 0.1,
    "praise": 0.8,
    "unclear": 0.0,
}

from pipeline.db import (
    get_connection, init_db, write_completed_record, write_call_entry,
    get_cache_origin, update_text_cache, get_record, get_completed_ids,
    get_pending_ids, DB_PATH
)

load_dotenv(Path(__file__).parent.parent / ".env")

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
GRADING_DIR = Path(__file__).parent.parent / "grading"

JEV_BASE_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-1.14.0"

CHECKPOINT_FILE = OUTPUTS_DIR / "checkpoint_state.json"
CHECKPOINT_INTERVAL = 500
MAX_WORKERS = 10  # v3 intent-only prompt is short; 10 workers safe at ~3.5 req/s each


def build_jev_request(review_text: str) -> dict:
    """Ask Jev for intent only. All other fields derived deterministically."""
    return {
        "model": JEV_MODEL,
        "state": review_text,
        "questions": {
            "intent": {
                "type": "choice",
                "instructions": "Intent? (cancellation>complaint>request>praise>unclear)",
                "criteria": {
                    "cancellation": "quitting/uninstalling/leaving",
                    "complaint": "problem/negative experience",
                    "request": "feature/change request",
                    "praise": "positive, no problem",
                    "unclear": "unrelated/gibberish"
                }
            }
        }
    }


def parse_jev_response(response: dict, review_text: str, review_id: str) -> dict:
    """Parse Jev intent response; derive topic/severity/sentiment from it."""
    answers = response["answers"]
    intent = answers["intent"]["choice"]
    assert intent in INTENTS, f"Invalid intent: {intent}"

    # Derive topic from TOPIC_KEYWORDS (keyword match, falls back to "other")
    topic = "other"
    max_hits = 0
    text_lower = review_text.lower()
    for t, keywords in TOPIC_KEYWORDS.items():
        if t == "other":
            continue
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > max_hits:
            max_hits = hits
            topic = t
    assert topic in TOPICS

    severity = INTENT_TO_SEVERITY[intent]
    sentiment = INTENT_TO_SENTIMENT[intent]
    needs_review = False

    evidence_quote = extract_quote(review_text)
    assert evidence_quote in review_text
    assert evidence_quote.strip()
    entities = [e for e in extract_entities(review_text, topic) if e.strip()]
    input_tokens = int(response.get("usage", {}).get("input_tokens", 0))
    output_tokens = int(response.get("usage", {}).get("output_tokens", 0))
    return {
        "topic": topic, "intent": intent, "severity": severity,
        "sentiment": sentiment, "needs_review": needs_review,
        "evidence_quote": evidence_quote, "entities": entities,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
    }


def call_jev(review_text: str, api_key: str, retries: int = 4) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = build_jev_request(review_text)
    for attempt in range(retries):
        try:
            resp = requests.post(JEV_BASE_URL, headers=headers, json=body, timeout=60)
            if resp.status_code == 402:
                raise RuntimeError(f"Jev budget exhausted (402): {resp.text[:200]}")
            if resp.status_code == 429:
                wait = 2 ** attempt + 1
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except RuntimeError:
            raise  # 402 budget errors: no retry
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Max retries exceeded")


def save_checkpoint(completed_ids: set):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({"completed_ids": sorted(completed_ids)}, f)


def _classify_one(review_id: str, review_text: str, source_sha256: str,
                  api_key: str, phase: str, db_path) -> dict:
    """Classify a single review. Called from thread pool."""
    ck = cache_key(review_text, LABEL_CONFIG)
    conn = get_connection(db_path)
    try:
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
                    phase=phase,
                )
                conn.commit()
                return {"review_id": review_id, "status": "cache_hit"}

        # Fresh classification
        request_id = f"enrich-{uuid.uuid4()}"
        try:
            jev_response = call_jev(review_text, api_key)
            parsed = parse_jev_response(jev_response, review_text, review_id)
        except Exception as e:
            write_call_entry(conn, request_id, "enrich", [review_id], JEV_MODEL,
                             phase, "failed", LABEL_CONFIG, 0, 0)
            conn.commit()
            return {"review_id": review_id, "status": "error", "error": str(e)}

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
            phase=phase,
        )
        write_call_entry(conn, request_id, "enrich", [review_id], JEV_MODEL,
                         phase, "succeeded", LABEL_CONFIG,
                         parsed["input_tokens"], parsed["output_tokens"])
        update_text_cache(conn, ck, review_id)
        conn.commit()
        return {"review_id": review_id, "status": "classified"}
    finally:
        conn.close()


def run(csv_path: str = None, db_path=None, max_records: int = None,
        save_checkpoint_before_path: str = None,
        save_checkpoint_after_path: str = None,
        is_resuming: bool = False,
        workers: int = MAX_WORKERS):

    OUTPUTS_DIR.mkdir(exist_ok=True)
    api_key = os.environ.get("TYPESAFE_API_KEY", "")
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY not set")

    conn = get_connection(db_path)
    completed_ids = set(get_completed_ids(conn))

    # Only load pending rows — avoid loading all 660K rows into memory
    rows = conn.execute(
        """SELECT rw.review_id, rw.source_sha256, rw.review_text
           FROM rows rw
           JOIN records rec ON rw.review_id = rec.review_id
           WHERE rec.status = 'pending'"""
    ).fetchall()
    conn.close()

    print(f"[Stage 2] Completed: {len(completed_ids):,}, Pending to process: {len(rows):,}, Workers: {workers}", flush=True)

    phase = "resume" if is_resuming else "initial"
    processed = 0
    errors = 0
    start_time = time.time()
    lock = threading.Lock()

    # Build work list (only pending, exclude already completed)
    work = []
    for row in rows:
        if row["review_id"] in completed_ids:
            continue
        if max_records is not None and len(work) >= max_records:
            break
        work.append((row["review_id"], row["review_text"], row["source_sha256"]))

    print(f"[Stage 2] Work queue: {len(work):,} reviews", flush=True)

    BATCH = 200  # submit this many futures at a time to avoid memory bloat
    total_work = len(work)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for batch_start in range(0, total_work, BATCH):
            batch = work[batch_start:batch_start + BATCH]
            futures = {
                executor.submit(_classify_one, rid, text, sha, api_key, phase, db_path): rid
                for rid, text, sha in batch
            }
            for future in as_completed(futures):
                result = future.result()
                with lock:
                    if result["status"] == "error":
                        errors += 1
                    else:
                        completed_ids.add(result["review_id"])
                        processed += 1

                    if processed % 1000 == 0 and processed > 0:
                        elapsed = time.time() - start_time
                        rate = processed / elapsed
                        remaining = total_work - processed
                        eta_min = int(remaining / rate / 60) if rate > 0 else 0
                        print(f"  [{processed:,}/{total_work:,}] {rate:.1f}/sec  ETA ~{eta_min}min", flush=True)
                        save_checkpoint(completed_ids)

    save_checkpoint(completed_ids)

    if save_checkpoint_before_path:
        GRADING_DIR.mkdir(exist_ok=True)
        with open(save_checkpoint_before_path, "w", encoding="utf-8") as f:
            json.dump({"completed_ids": sorted(completed_ids)}, f)
        print(f"[Stage 2] Saved checkpoint_before to {save_checkpoint_before_path}")

    if save_checkpoint_after_path:
        GRADING_DIR.mkdir(exist_ok=True)
        with open(save_checkpoint_after_path, "w", encoding="utf-8") as f:
            json.dump({"completed_ids": sorted(completed_ids)}, f)
        print(f"[Stage 2] Saved checkpoint_after to {save_checkpoint_after_path}")

    elapsed = time.time() - start_time
    print(f"[Stage 2] Done. Processed={processed:,}, Errors={errors}, "
          f"Total completed={len(completed_ids):,}, Time={elapsed:.0f}s")
    return {"processed": processed, "errors": errors, "total_completed": len(completed_ids)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--checkpoint-before", default=None)
    parser.add_argument("--checkpoint-after", default=None)
    args = parser.parse_args()
    run(
        db_path=args.db, max_records=args.max, is_resuming=args.resume,
        workers=args.workers,
        save_checkpoint_before_path=args.checkpoint_before,
        save_checkpoint_after_path=args.checkpoint_after,
    )
