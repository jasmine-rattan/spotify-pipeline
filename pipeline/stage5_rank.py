"""Stage 5: Deterministic ranking. No model calls."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import mean_string
from pipeline.db import get_connection, DB_PATH

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
GRADING_DIR = Path(__file__).parent.parent / "grading"


def run(db_path=None):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    GRADING_DIR.mkdir(exist_ok=True)

    conn = get_connection(db_path)

    # Load membership from grading/membership.csv
    membership_path = GRADING_DIR / "membership.csv"
    issues: dict[str, list] = {}

    with open(membership_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            issue_id = row["issue_id"]
            review_id = row["review_id"]
            if issue_id not in issues:
                issues[issue_id] = []
            issues[issue_id].append(review_id)

    # Load severity for each review_id
    severity_map = {}
    rows = conn.execute(
        "SELECT review_id, severity FROM records WHERE status = 'completed'"
    ).fetchall()
    for r in rows:
        severity_map[r["review_id"]] = int(r["severity"])

    ranking = []
    for issue_id, member_ids in issues.items():
        severities = [severity_map[rid] for rid in member_ids if rid in severity_map]
        complaint_count = len(severities)
        if complaint_count == 0:
            continue
        severity_sum = sum(severities)
        mean_sev = mean_string(severity_sum, complaint_count)
        priority_score = severity_sum  # integer, not float product

        ranking.append({
            "issue_id": issue_id,
            "complaint_count": complaint_count,
            "severity_sum": severity_sum,
            "mean_severity": mean_sev,
            "priority_score": priority_score,
        })

    # Sort: descending priority_score, then ascending issue_id for ties
    ranking.sort(key=lambda x: (-x["priority_score"], x["issue_id"]))

    # Write ranking.csv — ALL values as strings
    ranking_path = GRADING_DIR / "ranking.csv"
    fieldnames = ["rank", "issue_id", "complaint_count", "severity_sum", "mean_severity", "priority_score"]
    with open(ranking_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(ranking, 1):
            writer.writerow({
                "rank": str(i),
                "issue_id": row["issue_id"],
                "complaint_count": str(row["complaint_count"]),
                "severity_sum": str(row["severity_sum"]),
                "mean_severity": row["mean_severity"],
                "priority_score": str(row["priority_score"]),
            })

    # Also write to outputs/
    outputs_ranking_path = OUTPUTS_DIR / "ranking.csv"
    with open(outputs_ranking_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(ranking, 1):
            writer.writerow({
                "rank": str(i),
                "issue_id": row["issue_id"],
                "complaint_count": str(row["complaint_count"]),
                "severity_sum": str(row["severity_sum"]),
                "mean_severity": row["mean_severity"],
                "priority_score": str(row["priority_score"]),
            })

    print(f"[Stage 5] Ranking:")
    for i, row in enumerate(ranking, 1):
        print(f"  {i}. {row['issue_id']}: count={row['complaint_count']}, "
              f"severity_sum={row['severity_sum']}, mean={row['mean_severity']}")

    conn.close()
    return {"ranking": ranking}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    run(args.db)
