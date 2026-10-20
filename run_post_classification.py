"""Run stages 3-6 + export after Stage 2 completes."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from pipeline.db import get_connection, get_completed_ids, DB_PATH
from pipeline import stage3_verify, stage4_group, stage5_rank, stage6_recommend, stage2_keyword

GRADING_DIR = Path(__file__).parent / "grading"


def save_checkpoint_after():
    """Save all completed IDs to checkpoint_after.json."""
    conn = get_connection()
    completed = sorted(get_completed_ids(conn))
    conn.close()
    GRADING_DIR.mkdir(exist_ok=True)
    out = GRADING_DIR / "checkpoint_after.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"completed_ids": completed}, f)
    print(f"[Post] Saved checkpoint_after: {len(completed):,} IDs → {out}")
    return len(completed)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    parser.add_argument("--skip-verify", action="store_true")
    args = parser.parse_args()

    print("=== Post-classification pipeline ===")

    # Keyword fallback for any reviews still pending (budget exhaustion)
    print("\n[Post] Stage 2b: Keyword fallback for remaining pending records...")
    stage2_keyword.run(args.db)

    print("\n[Post] Saving checkpoint_after.json...")
    n = save_checkpoint_after()
    print(f"[Post] {n:,} completed records")

    if not args.skip_verify:
        print("\n[Post] Stage 3: Verify...")
        stage3_verify.run(args.db)

    print("\n[Post] Stage 4: Group...")
    stage4_group.run(args.db)

    print("\n[Post] Stage 5: Rank...")
    stage5_rank.run(args.db)

    print("\n[Post] Stage 6: Recommend...")
    stage6_recommend.run(args.db)

    print("\n[Post] Export grading artifacts...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "grading/export.py"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("EXPORT ERROR:", result.stderr)

    print("\n[Post] All done.")
