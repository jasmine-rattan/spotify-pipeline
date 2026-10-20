"""Stage 1: Parse CSV, quarantine empty texts, build cache map, populate DB."""
import csv
import json
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import row_sha, text_sha256, cache_key, LABEL_CONFIG
from pipeline.db import (
    init_db, get_connection, upsert_row, upsert_record_pending,
    upsert_record_quarantined, update_text_cache, DB_PATH
)

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
GRADING_DIR = Path(__file__).parent.parent / "grading"


def run(csv_path: str, db_path=None):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    GRADING_DIR.mkdir(exist_ok=True)

    conn = init_db(db_path)

    quarantine_records = []
    total = 0
    quarantined_count = 0
    pending_count = 0

    # text -> first review_id seen (for cache building)
    text_cache_map: dict[str, str] = {}

    print(f"[Stage 1] Reading CSV: {csv_path}")

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if total % 50000 == 0:
                print(f"  ...{total} rows read")

            sha = row_sha(row)
            review_id = row["review_id"]
            review_text = row["review_text"]

            if review_text.strip() == "":
                # Quarantine
                quarantined_count += 1
                upsert_record_quarantined(conn, review_id, sha, "empty_review_text")
                quarantine_records.append({
                    "review_id": review_id,
                    "source_sha256": sha,
                    "status": "quarantined",
                    "reason": "empty_review_text",
                })
            else:
                # Insert into rows table
                upsert_row(
                    conn,
                    review_id=review_id,
                    source_sha256=sha,
                    review_text=review_text,
                    review_rating=row["review_rating"],
                    review_likes=row["review_likes"],
                    app_version=row["app_version"],
                    review_timestamp=row["review_timestamp"],
                    text_sha256_val=text_sha256(review_text),
                )
                upsert_record_pending(conn, review_id, sha)
                pending_count += 1

                # Build text cache
                ck = cache_key(review_text, LABEL_CONFIG)
                if ck not in text_cache_map:
                    text_cache_map[ck] = review_id
                # We don't write to text_cache table yet — Stage 2 does that
                # as it classifies originals

    conn.commit()

    # Write quarantine.jsonl
    quarantine_path = OUTPUTS_DIR / "quarantine.jsonl"
    with open(quarantine_path, "w", encoding="utf-8") as f:
        for rec in quarantine_records:
            f.write(json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n")

    print(f"[Stage 1] Done. Total={total}, Quarantined={quarantined_count}, Pending={pending_count}")
    print(f"[Stage 1] Quarantine written to {quarantine_path}")

    conn.close()
    return {
        "total": total,
        "quarantined": quarantined_count,
        "pending": pending_count,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to spotify_reviews CSV")
    parser.add_argument("--db", default=None, help="Override DB path")
    args = parser.parse_args()
    run(args.csv, args.db)
