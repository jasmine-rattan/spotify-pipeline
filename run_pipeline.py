"""Entry point: runs all 6 stages of the Spotify review pipeline."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from pipeline import stage1_prepare, stage2_classify, stage3_verify
from pipeline import stage4_group, stage5_rank, stage6_recommend
from grading import export

DATASET_DIR = Path(__file__).parent.parent / "Final Assignment - Spotify Reviews Dataset"


def run_pilot(args):
    """Run on cost_100.csv with checkpoint demo."""
    print("=" * 60)
    print("PILOT MODE: 100-review pilot run")
    print("=" * 60)

    csv_path = str(DATASET_DIR / "cost_100.csv")

    # Stage 1
    print("\n[STAGE 1] Prepare")
    stage1_prepare.run(csv_path)

    # Stage 2: initial run (classify 50 reviews, save checkpoint_before)
    print("\n[STAGE 2] Classify — initial 50 reviews")
    grading_dir = Path(__file__).parent / "grading"
    grading_dir.mkdir(exist_ok=True)

    stage2_classify.run(
        max_records=50,
        is_resuming=False,
        save_checkpoint_before_path=str(grading_dir / "checkpoint_before.json"),
    )

    # Stage 2: resume — classify remaining 50 reviews
    print("\n[STAGE 2] Classify — resume remaining 50 reviews")
    stage2_classify.run(
        max_records=50,
        is_resuming=True,
        save_checkpoint_after_path=str(grading_dir / "checkpoint_after.json"),
    )

    print("\nPilot run complete.")


def run_checkpoint_demo(args):
    """
    Checkpoint demo using cost_100.csv for initial + checkpoint_500.csv for resume.
    1. Classify cost_100 reviews → save checkpoint_before
    2. Interrupt
    3. Add checkpoint_500 reviews to DB
    4. Resume → phase='resume' → save checkpoint_after
    """
    print("=" * 60)
    print("CHECKPOINT DEMO MODE")
    print("=" * 60)

    grading_dir = Path(__file__).parent / "grading"
    grading_dir.mkdir(exist_ok=True)

    # Phase 1: cost_100 initial classification
    csv_100 = str(DATASET_DIR / "cost_100.csv")
    print("\n[Phase 1] Stage 1 on cost_100.csv")
    stage1_prepare.run(csv_100)

    print("\n[Phase 1] Stage 2 — classify 100 reviews (initial phase)")
    stage2_classify.run(
        is_resuming=False,
        save_checkpoint_before_path=str(grading_dir / "checkpoint_before.json"),
    )

    # Simulate interruption: add more reviews from checkpoint_500.csv
    print("\n[Phase 2] Adding checkpoint_500.csv reviews to DB...")
    csv_500 = str(DATASET_DIR / "checkpoint_500.csv")
    stage1_prepare.run(csv_500)  # Adds new pending reviews

    # Resume
    print("\n[Phase 2] Stage 2 — resume with additional reviews (resume phase)")
    stage2_classify.run(
        is_resuming=True,
        save_checkpoint_after_path=str(grading_dir / "checkpoint_after.json"),
    )

    print("\nCheckpoint demo complete.")


def run_full(args):
    """Full pipeline run on the complete 660K dataset."""
    print("=" * 60)
    print("FULL PIPELINE RUN")
    print("=" * 60)

    csv_path = args.csv or str(DATASET_DIR / "spotify_reviews_18months.csv")
    grading_dir = Path(__file__).parent / "grading"
    grading_dir.mkdir(exist_ok=True)

    # Stage 1
    print("\n[STAGE 1] Prepare CSV")
    result = stage1_prepare.run(csv_path)
    print(f"  Total: {result['total']}, Quarantined: {result['quarantined']}, Pending: {result['pending']}")

    # Generate ingestion.json
    print("\n[INGESTION] Generating ingestion.json...")
    import subprocess, os
    check_script = str(DATASET_DIR / "check_submission.py")
    result_proc = subprocess.run(
        [sys.executable, check_script, "profile", "--full", csv_path, "--out", str(grading_dir / "ingestion.json")],
        capture_output=True, text=True
    )
    if result_proc.returncode == 0:
        print("  ingestion.json generated")
    else:
        print(f"  WARNING: {result_proc.stderr}")

    # Stage 2 — initial classification
    print("\n[STAGE 2] Classify — initial run")
    stage2_classify.run(
        is_resuming=False,
        save_checkpoint_before_path=str(grading_dir / "checkpoint_before.json"),
    )

    # Stage 3
    print("\n[STAGE 3] Verify")
    stage3_verify.run()

    # Stage 4
    print("\n[STAGE 4] Group")
    stage4_group.run()

    # Stage 5
    print("\n[STAGE 5] Rank")
    stage5_rank.run()

    # Stage 6
    print("\n[STAGE 6] Recommend")
    stage6_recommend.run()

    # Export
    print("\n[EXPORT] Generating grading artifacts")
    export.run()

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spotify Review Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    pilot_parser = subparsers.add_parser("pilot", help="Run on 100-review pilot CSV")
    pilot_parser.set_defaults(func=run_pilot)

    demo_parser = subparsers.add_parser("checkpoint-demo", help="Run checkpoint interruption demo")
    demo_parser.set_defaults(func=run_checkpoint_demo)

    full_parser = subparsers.add_parser("full", help="Run full pipeline on complete dataset")
    full_parser.add_argument("--csv", default=None, help="Override CSV path")
    full_parser.set_defaults(func=run_full)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)
