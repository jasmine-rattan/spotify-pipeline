"""Cost calculator: offline replay and pilot mode."""
import csv
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

COST_DIR = Path(__file__).parent
RATES_PATH = COST_DIR / "rates.csv"
USAGE_PATH = COST_DIR / "usage.csv"
REPORT_PATH = COST_DIR / "report.md"


def load_rates() -> dict:
    rates = {}
    if not RATES_PATH.exists():
        return rates
    with open(RATES_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rates[row["model"]] = {
                "input_per_mtok": Decimal(row["input_per_mtok"]),
                "output_per_mtok": Decimal(row["output_per_mtok"]),
            }
    return rates


def load_usage() -> list:
    if not USAGE_PATH.exists():
        return []
    with open(USAGE_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def calc_cost(input_tokens: int, output_tokens: int, model: str, rates: dict) -> Decimal:
    r = rates.get(model)
    if not r:
        return Decimal("0")
    cost = (Decimal(input_tokens) / Decimal(1_000_000)) * r["input_per_mtok"]
    cost += (Decimal(output_tokens) / Decimal(1_000_000)) * r["output_per_mtok"]
    return cost


def run_offline():
    """Replay calls.jsonl to compute cost without API calls."""
    grading_dir = Path(__file__).parent.parent / "grading"
    calls_path = grading_dir / "calls.jsonl"
    rates = load_rates()

    if not calls_path.exists():
        print(f"[Cost] calls.jsonl not found at {calls_path}")
        return

    total_cost = Decimal("0")
    by_model = {}
    total_tokens_in = 0
    total_tokens_out = 0

    with open(calls_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            call = json.loads(line)
            model = call.get("model", "")
            ti = int(call.get("input_tokens", 0))
            to = int(call.get("output_tokens", 0))
            cost = calc_cost(ti, to, model, rates)
            total_cost += cost
            total_tokens_in += ti
            total_tokens_out += to
            if model not in by_model:
                by_model[model] = {"input": 0, "output": 0, "cost": Decimal("0")}
            by_model[model]["input"] += ti
            by_model[model]["output"] += to
            by_model[model]["cost"] += cost

    print(f"\n=== Cost Summary (Offline Replay) ===")
    for model, data in by_model.items():
        print(f"  {model}: ${data['cost']:.4f} "
              f"({data['input']:,} in + {data['output']:,} out tokens)")
    print(f"  TOTAL: ${total_cost:.4f}")
    print(f"  Total input tokens: {total_tokens_in:,}")
    print(f"  Total output tokens: {total_tokens_out:,}")


def run_pilot(csv_path: str):
    """Run pipeline on 100 reviews and measure cost."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    from pipeline import stage1_prepare, stage2_classify

    print("[Cost Pilot] Running on 100-review CSV...")

    # Stage 1
    stage1_prepare.run(csv_path)

    # Stage 2: time the classification
    import time
    start = time.time()
    result = stage2_classify.run()
    elapsed = time.time() - start

    print(f"[Cost Pilot] Classification took {elapsed:.1f}s for {result['processed']} reviews")

    # Calculate from calls
    run_offline()


def project_full_run(avg_input_per_review: int = 350, avg_output_per_review: int = 80,
                     total_reviews: int = 660609, distinct_reviews: int = 484189):
    """Project costs for full 660K run with and without deduplication."""
    rates = load_rates()

    jev_model = "jev-1.14.0"
    haiku_model = "claude-haiku-4-5-20251001"

    # Haiku calls: 2 (group + memo), minimal tokens
    haiku_in = 1500
    haiku_out = 1000

    print("\n=== Full Run Cost Projections ===")

    # Cold run (no cache)
    cold_jev_cost = calc_cost(
        avg_input_per_review * total_reviews,
        avg_output_per_review * total_reviews,
        jev_model, rates
    )
    cold_haiku_cost = calc_cost(haiku_in, haiku_out, haiku_model, rates)
    print(f"\nCold (uncached, {total_reviews:,} reviews):")
    print(f"  Jev: ${cold_jev_cost:.2f}")
    print(f"  Haiku: ${cold_haiku_cost:.4f}")
    print(f"  Total: ${cold_jev_cost + cold_haiku_cost:.2f}")

    # With dedup (only distinct texts classified)
    dedup_jev_cost = calc_cost(
        avg_input_per_review * distinct_reviews,
        avg_output_per_review * distinct_reviews,
        jev_model, rates
    )
    print(f"\nWith dedup ({distinct_reviews:,} distinct texts):")
    print(f"  Jev: ${dedup_jev_cost:.2f}")
    print(f"  Haiku: ${cold_haiku_cost:.4f}")
    print(f"  Total: ${dedup_jev_cost + cold_haiku_cost:.2f}")
    print(f"  Savings: ${cold_jev_cost - dedup_jev_cost:.2f} ({(1 - distinct_reviews/total_reviews)*100:.1f}% reduction)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Replay calls.jsonl")
    parser.add_argument("--pilot", action="store_true", help="Run 100-review pilot")
    parser.add_argument("--csv", default=None, help="CSV path for pilot")
    parser.add_argument("--project", action="store_true", help="Show full-run projections")
    args = parser.parse_args()

    if args.offline:
        run_offline()
    elif args.pilot:
        if not args.csv:
            print("--csv required for pilot mode")
            sys.exit(1)
        run_pilot(args.csv)
    elif args.project:
        project_full_run()
    else:
        parser.print_help()
