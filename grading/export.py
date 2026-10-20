"""Grading export: generates all required grading/ folder contents."""
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.db import get_connection, get_all_records, get_all_calls, get_review_text, DB_PATH

GRADING_DIR = Path(__file__).parent
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"

# Exact hardcoded run.json content
RUN_JSON = {
    "version": "a5-audit-v1",
    "analysis_count": 660622,
    "analysis_sha256": "1fc85de68a304dd8978b537cfa58793d5f41cbaf417fa32cb53899f83a2fcef6",
    "classification_input_fields": ["review_text"],
    "allow_multi_issue": False,
}

COMPLETED_FIELDS = [
    "review_id", "source_sha256", "status", "topic", "intent",
    "sentiment", "severity", "entities", "evidence_quote",
    "needs_review", "label_config", "cache_source_id"
]


def run(db_path=None):
    GRADING_DIR.mkdir(exist_ok=True)

    conn = get_connection(db_path)

    # 1. run.json
    run_path = GRADING_DIR / "run.json"
    with open(run_path, "w", encoding="utf-8") as f:
        json.dump(RUN_JSON, f, ensure_ascii=False, allow_nan=False)
    print(f"[Export] Wrote {run_path}")

    # 2. records.jsonl
    records_path = GRADING_DIR / "records.jsonl"
    all_records = get_all_records(conn)

    # Preload all review texts in a single query to avoid N+1 problem
    print(f"[Export] Preloading review texts...")
    text_map = {}
    for row_r in conn.execute("SELECT review_id, review_text FROM rows"):
        text_map[row_r["review_id"]] = row_r["review_text"]
    print(f"[Export] Loaded {len(text_map):,} review texts")

    with open(records_path, "w", encoding="utf-8") as f:
        for row in all_records:
            if row["status"] == "completed":
                # Validate and serialize
                entities = json.loads(row["entities"]) if row["entities"] else []
                entities = [e for e in entities if e.strip()]

                needs_review = bool(row["needs_review"])
                sentiment = float(row["sentiment"])
                assert math.isfinite(sentiment), f"Non-finite sentiment: {row['review_id']}"
                assert -1.0 <= sentiment <= 1.0, f"Sentiment out of range: {row['review_id']}"
                severity = int(row["severity"])

                source_text = text_map.get(row["review_id"], "")
                evidence_quote = row["evidence_quote"]
                assert evidence_quote in source_text, f"quote not in text: {row['review_id']}"
                assert evidence_quote.strip(), f"empty quote: {row['review_id']}"

                entry = {
                    "review_id": row["review_id"],
                    "source_sha256": row["source_sha256"],
                    "status": "completed",
                    "topic": row["topic"],
                    "intent": row["intent"],
                    "sentiment": sentiment,
                    "severity": severity,
                    "entities": entities,
                    "evidence_quote": evidence_quote,
                    "needs_review": needs_review,
                    "label_config": row["label_config"],
                }
                if row.get("cache_source_id"):
                    entry["cache_source_id"] = row["cache_source_id"]

                f.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")

            elif row["status"] == "quarantined":
                entry = {
                    "review_id": row["review_id"],
                    "source_sha256": row["source_sha256"],
                    "status": "quarantined",
                    "reason": row["reason"],
                }
                f.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")

    print(f"[Export] Wrote {records_path} ({len(all_records)} records)")

    # 3. calls.jsonl
    calls_path = GRADING_DIR / "calls.jsonl"
    all_calls = get_all_calls(conn)

    with open(calls_path, "w", encoding="utf-8") as f:
        for call in all_calls:
            entry = {
                "request_id": call["request_id"],
                "role": call["role"],
                "review_ids": json.loads(call["review_ids"]),
                "model": call["model"],
                "outcome": call["outcome"],
                "label_config": call["label_config"],
                "input_tokens": int(call["input_tokens"]),
                "output_tokens": int(call["output_tokens"]),
            }
            # Include phase for enrich calls only
            if call["role"] == "enrich" and call["phase"] is not None:
                entry["phase"] = call["phase"]

            f.write(json.dumps(entry, allow_nan=False) + "\n")

    print(f"[Export] Wrote {calls_path} ({len(all_calls)} calls)")

    # 4. Validate checkpoint files exist
    before_path = GRADING_DIR / "checkpoint_before.json"
    after_path = GRADING_DIR / "checkpoint_after.json"

    if before_path.exists() and after_path.exists():
        with open(before_path) as f:
            before = set(json.load(f).get("completed_ids", []))
        with open(after_path) as f:
            after = set(json.load(f).get("completed_ids", []))

        # Validate: before ⊂ after
        if not before < after:
            print(f"[Export] WARNING: checkpoint_before is NOT a proper subset of checkpoint_after")
        else:
            print(f"[Export] Checkpoints valid: before={len(before)}, after={len(after)}")
    else:
        print(f"[Export] WARNING: checkpoint files missing")

    conn.close()
    print(f"[Export] Done. Grading folder: {GRADING_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    run(args.db)
