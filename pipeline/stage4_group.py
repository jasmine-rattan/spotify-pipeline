"""Stage 4: Group complaints into issues by topic. Haiku call for naming."""
import csv
import json
import os
import sys
import uuid
from pathlib import Path

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.db import get_connection, write_call_entry, count_completed_complaints, DB_PATH

load_dotenv(Path(__file__).parent.parent / ".env")

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
GRADING_DIR = Path(__file__).parent.parent / "grading"

HAIKU_MODEL = "claude-haiku-4-5-20251001"
GROUP_LABEL_CONFIG = f"{HAIKU_MODEL}+group-v1"


def run(db_path=None):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    GRADING_DIR.mkdir(exist_ok=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    conn = get_connection(db_path)

    # Get all completed complaints/cancellations
    complaints = conn.execute(
        """SELECT r.review_id, r.topic, r.severity, r.intent, r.evidence_quote
           FROM records r
           WHERE r.status = 'completed'
             AND r.intent IN ('complaint', 'cancellation')"""
    ).fetchall()
    complaints = [dict(c) for c in complaints]

    print(f"[Stage 4] Total complaints/cancellations: {len(complaints)}")

    # Group by topic -> issue_id
    issues: dict[str, list] = {}
    for rec in complaints:
        issue_id = f"issue-{rec['topic']}"
        if issue_id not in issues:
            issues[issue_id] = []
        issues[issue_id].append(rec)

    # Verify all complaints are grouped
    all_complaint_count = count_completed_complaints(conn)
    total_in_issues = sum(len(v) for v in issues.values())
    assert all_complaint_count == total_in_issues, (
        f"Ungrouped complaints: {all_complaint_count} != {total_in_issues}"
    )

    # Check no duplicate (issue_id, review_id) pairs
    pairs = set()
    for issue_id, members in issues.items():
        for rec in members:
            pair = (issue_id, rec["review_id"])
            assert pair not in pairs, f"Duplicate membership: {pair}"
            pairs.add(pair)

    print(f"[Stage 4] Issues: {list(issues.keys())}")

    # Build evidence pack: 3 shortest quotes per issue for Haiku
    evidence = {}
    for issue_id, members in issues.items():
        quotes = [r["evidence_quote"] for r in sorted(members, key=lambda x: len(x["evidence_quote"]))[:3]]
        evidence[issue_id] = quotes

    # Claude Haiku call for issue naming
    prompt = _build_group_prompt(evidence)
    client = anthropic.Anthropic(api_key=api_key)
    request_id = f"group-{uuid.uuid4()}"

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        group_names_text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        outcome = "succeeded"
        print(f"[Stage 4] Haiku group call succeeded")
    except Exception as e:
        print(f"[Stage 4] Haiku call failed: {e}")
        group_names_text = ""
        input_tokens = 0
        output_tokens = 0
        outcome = "failed"

    write_call_entry(
        conn,
        request_id=request_id,
        role="group",
        review_ids=[],
        model=HAIKU_MODEL,
        phase=None,
        outcome=outcome,
        label_config=GROUP_LABEL_CONFIG,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    conn.commit()

    # Parse Haiku response into issue names
    issue_names = _parse_group_names(group_names_text, issues)

    # Write membership.csv
    membership_path = GRADING_DIR / "membership.csv"
    with open(membership_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["issue_id", "review_id"])
        for issue_id, members in sorted(issues.items()):
            for rec in members:
                writer.writerow([issue_id, rec["review_id"]])

    # Write issues.csv (with names) to outputs
    issues_path = OUTPUTS_DIR / "issues.csv"
    with open(issues_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["issue_id", "issue_name", "complaint_count"])
        for issue_id in sorted(issues.keys()):
            writer.writerow([issue_id, issue_names.get(issue_id, issue_id), len(issues[issue_id])])

    # Write aggregates.csv
    aggregates_path = OUTPUTS_DIR / "aggregates.csv"
    with open(aggregates_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["issue_id", "issue_name", "complaint_count", "severity_sum"])
        for issue_id in sorted(issues.keys()):
            sev_sum = sum(r["severity"] for r in issues[issue_id])
            writer.writerow([issue_id, issue_names.get(issue_id, issue_id),
                             len(issues[issue_id]), sev_sum])

    print(f"[Stage 4] Membership written to {membership_path}")
    conn.close()
    return {"issues": list(issues.keys()), "total_complaints": total_in_issues}


def _build_group_prompt(evidence: dict) -> str:
    lines = ["Give each Spotify issue group a short, descriptive 3-5 word display name.\n",
             "Respond with exactly one line per group in this format: issue_id: Display Name\n"]
    for issue_id, quotes in sorted(evidence.items()):
        lines.append(f"\n{issue_id}:")
        for q in quotes:
            lines.append(f"  - \"{q[:150]}\"")
    return "\n".join(lines)


def _parse_group_names(text: str, issues: dict) -> dict:
    names = {iid: iid for iid in issues}
    if not text:
        return names
    for line in text.strip().split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        parts = line.split(":", 1)
        iid = parts[0].strip()
        name = parts[1].strip()
        if iid in issues:
            names[iid] = name
        else:
            for issue_id in issues:
                if iid in issue_id or issue_id in iid:
                    names[issue_id] = name
                    break
    return names


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    run(args.db)
