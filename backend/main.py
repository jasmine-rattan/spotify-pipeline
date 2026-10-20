"""FastAPI backend serving pre-computed pipeline artifacts."""
import csv
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Spotify Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
OUTPUTS_DIR = BASE_DIR.parent / "outputs"
GRADING_DIR = BASE_DIR.parent / "grading"


def load_ranking() -> list:
    ranking_path = GRADING_DIR / "ranking.csv"
    if not ranking_path.exists():
        return []
    with open(ranking_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_issues() -> list:
    issues_path = OUTPUTS_DIR / "issues.csv"
    if not issues_path.exists():
        return []
    with open(issues_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_memo() -> str:
    memo_path = OUTPUTS_DIR / "memo.md"
    if not memo_path.exists():
        return "Memo not yet generated."
    return memo_path.read_text(encoding="utf-8")


def load_records_summary() -> dict:
    """Load summary stats — uses pre-computed metrics.json if available."""
    metrics_path = OUTPUTS_DIR / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path, encoding="utf-8") as f:
            return json.load(f)

    # Fallback: compute from records.jsonl (slow for large files)
    records_path = GRADING_DIR / "records.jsonl"
    if not records_path.exists():
        return {}

    total = 0
    completed = 0
    quarantined = 0
    topic_counts: dict = {}
    intent_counts: dict = {}

    with open(records_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            total += 1
            status = rec.get("status")
            if status == "completed":
                completed += 1
                t = rec.get("topic", "other")
                topic_counts[t] = topic_counts.get(t, 0) + 1
                i = rec.get("intent", "unclear")
                intent_counts[i] = intent_counts.get(i, 0) + 1
            elif status == "quarantined":
                quarantined += 1

    return {
        "total": total,
        "completed": completed,
        "quarantined": quarantined,
        "topic_counts": topic_counts,
        "intent_counts": intent_counts,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/metrics")
def metrics():
    summary = load_records_summary()
    return JSONResponse(content=summary)


@app.get("/api/issues")
def issues():
    return JSONResponse(content=load_issues())


@app.get("/api/ranking")
def ranking():
    return JSONResponse(content=load_ranking())


@app.get("/api/recommendations")
def recommendations():
    return JSONResponse(content={"memo": load_memo()})
