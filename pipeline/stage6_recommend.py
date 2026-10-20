"""Stage 6: Claude Haiku generates the product memo. claims.csv from ranking."""
import csv
import json
import os
import sys
import uuid
from pathlib import Path

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.db import get_connection, write_call_entry, DB_PATH

load_dotenv(Path(__file__).parent.parent / ".env")

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
GRADING_DIR = Path(__file__).parent.parent / "grading"

HAIKU_MODEL = "claude-haiku-4-5-20251001"
MEMO_LABEL_CONFIG = f"{HAIKU_MODEL}+memo-v1"


def run(db_path=None):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    GRADING_DIR.mkdir(exist_ok=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    conn = get_connection(db_path)

    # Load ranking
    ranking_path = GRADING_DIR / "ranking.csv"
    ranking = []
    with open(ranking_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ranking.append(row)

    print(f"[Stage 6] Loaded {len(ranking)} ranked issues")

    # Load issue names
    issue_names = {}
    issues_csv = OUTPUTS_DIR / "issues.csv"
    if issues_csv.exists():
        with open(issues_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                issue_names[row["issue_id"]] = row["issue_name"]

    top_issues = ranking[:5]

    # Get 3 shortest evidence quotes per top issue
    evidence_quotes = {}
    for row in top_issues:
        issue_id = row["issue_id"]
        members = conn.execute(
            """SELECT rec.evidence_quote
               FROM records rec
               WHERE rec.status = 'completed'
                 AND rec.intent IN ('complaint', 'cancellation')
                 AND rec.topic = ?
               ORDER BY LENGTH(rec.evidence_quote) ASC
               LIMIT 3""",
            (issue_id.replace("issue-", ""),)
        ).fetchall()
        evidence_quotes[issue_id] = [r["evidence_quote"] for r in members]

    # Build memo prompt (bounded: top 5 issues + 3 quotes each, < 2000 tokens)
    memo_prompt = _build_memo_prompt(top_issues, issue_names, evidence_quotes)

    client = anthropic.Anthropic(api_key=api_key)
    request_id = f"memo-{uuid.uuid4()}"

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": memo_prompt}]
        )
        memo_text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        outcome = "succeeded"
        print(f"[Stage 6] Haiku memo call succeeded ({input_tokens} in, {output_tokens} out tokens)")
    except Exception as e:
        print(f"[Stage 6] Haiku memo call failed: {e}")
        memo_text = _fallback_memo(top_issues, issue_names)
        input_tokens = 0
        output_tokens = 0
        outcome = "failed"

    write_call_entry(
        conn,
        request_id=request_id,
        role="memo",
        review_ids=[],
        model=HAIKU_MODEL,
        phase=None,
        outcome=outcome,
        label_config=MEMO_LABEL_CONFIG,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    conn.commit()

    # Write memo.md
    memo_path = OUTPUTS_DIR / "memo.md"
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write(memo_text)

    # Write claims.csv — one row per metric per cited issue (all top 5 × 4 metrics)
    claims_path = GRADING_DIR / "claims.csv"
    metrics = ["complaint_count", "severity_sum", "mean_severity", "priority_score"]
    claim_num = 0
    with open(claims_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["claim_id", "issue_id", "metric", "value"])
        for row in top_issues:
            issue_id = row["issue_id"]
            for metric in metrics:
                claim_num += 1
                claim_id = f"claim-{claim_num:03d}"
                writer.writerow([claim_id, issue_id, metric, row[metric]])

    print(f"[Stage 6] Memo written to {memo_path}")
    print(f"[Stage 6] Claims written to {claims_path} ({claim_num} claims)")
    conn.close()
    return {"memo_length": len(memo_text), "claims_count": claim_num}


def _build_memo_prompt(top_issues: list, issue_names: dict, evidence_quotes: dict) -> str:
    lines = [
        "You are a product manager at Spotify. Write a concise product memo (300-500 words) "
        "recommending the top issues to fix based on this analysis of 660,622 app reviews.\n",
        "For each issue cited, include the claim ID in parentheses exactly as shown (e.g. claim-001).\n",
        "## Top Issues by Priority Score\n",
    ]
    claim_num = 0
    for row in top_issues:
        issue_id = row["issue_id"]
        name = issue_names.get(issue_id, issue_id)
        lines.append(f"\n### {name} ({issue_id})")
        for metric in ["complaint_count", "severity_sum", "mean_severity", "priority_score"]:
            claim_num += 1
            lines.append(f"- {metric}: {row[metric]} (claim-{claim_num:03d})")
        for q in evidence_quotes.get(issue_id, []):
            lines.append(f'- Example: "{q[:150]}"')
    lines.append("\n\nWrite the product memo now, citing claim IDs inline:")
    return "\n".join(lines)


def _fallback_memo(top_issues: list, issue_names: dict) -> str:
    lines = ["# Spotify App Review Analysis — Product Memo\n",
             "## Top Issues\n"]
    claim_num = 0
    for row in top_issues:
        issue_id = row["issue_id"]
        name = issue_names.get(issue_id, issue_id)
        lines.append(f"\n### {name}")
        for metric in ["complaint_count", "severity_sum", "mean_severity", "priority_score"]:
            claim_num += 1
            lines.append(f"- {metric}: {row[metric]} (claim-{claim_num:03d})")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    run(args.db)
