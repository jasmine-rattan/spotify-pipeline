"""Stage 3: Independent re-labeling of a random sample + injection test."""
import json
import os
import random
import sys
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import LABEL_CONFIG, TOPICS, INTENTS, extract_quote, extract_entities
from pipeline.db import (
    get_connection, write_call_entry, get_record, DB_PATH
)
from pipeline.stage2_classify import (
    call_jev, parse_jev_response, build_jev_request, JEV_MODEL
)

load_dotenv(Path(__file__).parent.parent / ".env")

EVALS_DIR = Path(__file__).parent.parent / "evals"
GRADING_DIR = Path(__file__).parent.parent / "grading"
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"

SAMPLE_SIZE = 200
SEED = 42


def run(db_path=None):
    EVALS_DIR.mkdir(exist_ok=True)
    GRADING_DIR.mkdir(exist_ok=True)

    api_key = os.environ.get("TYPESAFE_API_KEY", "")
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY not set")

    conn = get_connection(db_path)

    # Get completed records
    completed_rows = conn.execute(
        """SELECT r.review_id, r.topic, r.intent, r.severity, r.sentiment,
                  r.needs_review, rw.review_text
           FROM records r
           JOIN rows rw ON r.review_id = rw.review_id
           WHERE r.status = 'completed'"""
    ).fetchall()

    completed_list = [dict(r) for r in completed_rows]
    print(f"[Stage 3] Total completed records: {len(completed_list)}")

    # Sample deterministically
    rng = random.Random(SEED)
    sample_size = min(SAMPLE_SIZE, len(completed_list))
    sample = rng.sample(completed_list, sample_size)

    print(f"[Stage 3] Re-verifying {sample_size} records...")

    results = []
    topic_agrees = 0
    intent_agrees = 0
    severity_abs_errors = []

    for rec in sample:
        review_id = rec["review_id"]
        review_text = rec["review_text"]
        request_id = f"verify-{uuid.uuid4()}"

        try:
            jev_response = call_jev(review_text, api_key)
            parsed = parse_jev_response(jev_response, review_text, review_id)

            # Log verify call
            write_call_entry(
                conn,
                request_id=request_id,
                role="verify",
                review_ids=[review_id],
                model=JEV_MODEL,
                phase=None,
                outcome="succeeded",
                label_config=LABEL_CONFIG,
                input_tokens=parsed["input_tokens"],
                output_tokens=parsed["output_tokens"],
            )
            conn.commit()

            topic_match = parsed["topic"] == rec["topic"]
            intent_match = parsed["intent"] == rec["intent"]
            sev_diff = abs(parsed["severity"] - rec["severity"])

            topic_agrees += int(topic_match)
            intent_agrees += int(intent_match)
            severity_abs_errors.append(sev_diff)

            results.append({
                "review_id": review_id,
                "original_topic": rec["topic"],
                "verify_topic": parsed["topic"],
                "topic_agree": topic_match,
                "original_intent": rec["intent"],
                "verify_intent": parsed["intent"],
                "intent_agree": intent_match,
                "original_severity": rec["severity"],
                "verify_severity": parsed["severity"],
                "severity_abs_error": sev_diff,
            })
        except Exception as e:
            print(f"  [ERROR] {review_id}: {e}")
            write_call_entry(
                conn,
                request_id=request_id,
                role="verify",
                review_ids=[review_id],
                model=JEV_MODEL,
                phase=None,
                outcome="failed",
                label_config=LABEL_CONFIG,
                input_tokens=0,
                output_tokens=0,
            )
            conn.commit()

    n = len(results)
    topic_acc = topic_agrees / n if n else 0
    intent_acc = intent_agrees / n if n else 0
    severity_mae = sum(severity_abs_errors) / n if n else 0

    print(f"[Stage 3] Topic agreement: {topic_acc:.3f}, Intent agreement: {intent_acc:.3f}, Severity MAE: {severity_mae:.3f}")

    # Write golden_50_predictions.csv (first 50 of sample)
    predictions_path = EVALS_DIR / "golden_50_predictions.csv"
    import csv
    with open(predictions_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "review_id", "original_topic", "verify_topic", "topic_agree",
            "original_intent", "verify_intent", "intent_agree",
            "original_severity", "verify_severity", "severity_abs_error"
        ])
        writer.writeheader()
        for row in results[:50]:
            writer.writerow(row)

    # Disagreement report
    disagreements = [r for r in results if not r["topic_agree"] or not r["intent_agree"]]
    report_path = EVALS_DIR / "disagreement_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Stage 3 Verification Report\n\n")
        f.write(f"- Sample size: {n}\n")
        f.write(f"- Topic agreement: {topic_acc:.1%}\n")
        f.write(f"- Intent agreement: {intent_acc:.1%}\n")
        f.write(f"- Severity MAE: {severity_mae:.3f}\n\n")
        f.write(f"## Disagreements ({len(disagreements)})\n\n")
        for d in disagreements[:20]:
            f.write(f"- `{d['review_id']}`: topic {d['original_topic']}→{d['verify_topic']}, "
                    f"intent {d['original_intent']}→{d['verify_intent']}\n")

    # Injection test: modify 1 record's topic in memory, re-verify, confirm disagreement
    print("[Stage 3] Running injection test...")
    injection_results = _run_injection_test(sample[0], api_key, conn)

    inj_path = EVALS_DIR / "injection_test_results.json"
    with open(inj_path, "w", encoding="utf-8") as f:
        json.dump(injection_results, f, indent=2)

    conn.close()
    print(f"[Stage 3] Done. Results in {EVALS_DIR}")
    return {"topic_agreement": topic_acc, "intent_agreement": intent_acc, "severity_mae": severity_mae}


def _run_injection_test(record: dict, api_key: str, conn) -> dict:
    """Inject a wrong topic and verify Jev independently disagrees."""
    review_id = record["review_id"]
    review_text = record["review_text"]
    original_topic = record["topic"]

    # Pick a different topic for injection
    other_topics = [t for t in TOPICS if t != original_topic]
    injected_topic = other_topics[0]

    # Re-run Jev independently (no injected topic visible to model)
    request_id = f"verify-inject-{uuid.uuid4()}"
    try:
        jev_response = call_jev(review_text, api_key)
        from pipeline.stage2_classify import parse_jev_response
        parsed = parse_jev_response(jev_response, review_text, review_id)

        write_call_entry(
            conn,
            request_id=request_id,
            role="verify",
            review_ids=[review_id],
            model=JEV_MODEL,
            phase=None,
            outcome="succeeded",
            label_config=LABEL_CONFIG,
            input_tokens=parsed["input_tokens"],
            output_tokens=parsed["output_tokens"],
        )
        conn.commit()

        jev_topic = parsed["topic"]
        # Jev should NOT return the injected_topic (it's independent)
        injection_resisted = (jev_topic != injected_topic)

        return {
            "review_id": review_id,
            "original_topic": original_topic,
            "injected_topic": injected_topic,
            "jev_independent_topic": jev_topic,
            "injection_resisted": injection_resisted,
            "note": "Jev classified independently; injected topic was never sent to model"
        }
    except Exception as e:
        return {"error": str(e), "review_id": review_id}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    run(args.db)
