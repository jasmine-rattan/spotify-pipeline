"""Offline ranking regeneration — no API calls needed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from pipeline import stage4_group, stage5_rank

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Regenerate ranking from existing DB")
    parser.add_argument("--db", default=None)
    args = parser.parse_args()

    print("[Ranking] Stage 4: Group")
    stage4_group.run(args.db)
    print("[Ranking] Stage 5: Rank")
    result = stage5_rank.run(args.db)
    print("[Ranking] Done:", result)
