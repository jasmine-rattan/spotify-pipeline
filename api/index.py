"""
Vercel serverless backend for the Spotify pipeline.
Reads from pre-computed database outputs (committed artifacts).
The "database" is the SQLite pipeline.db; its outputs are exported to:
  - outputs/metrics.json (aggregated counts by topic/intent)
  - outputs/issues.csv   (issue names from Haiku group call)
  - outputs/memo.md      (AI-generated product memo)
  - grading/ranking.csv  (baseline ranking)
"""
import csv
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler

# Paths relative to project root (where Vercel runs from)
ROOT = Path(__file__).parent.parent
OUTPUTS = ROOT / "outputs"
GRADING = ROOT / "grading"


def _cors(handler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Type", "application/json")


def _json_response(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    _cors(handler)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def load_metrics():
    p = OUTPUTS / "metrics.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


def load_ranking():
    p = GRADING / "ranking.csv"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_issues():
    p = OUTPUTS / "issues.csv"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_memo():
    p = OUTPUTS / "memo.md"
    return p.read_text(encoding="utf-8") if p.exists() else "Memo not generated."


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        _cors(self)
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path in ("/api/health", "/api"):
            _json_response(self, {"status": "ok", "version": "1.0.0"})

        elif path == "/api/metrics":
            _json_response(self, load_metrics())

        elif path == "/api/issues":
            _json_response(self, load_issues())

        elif path == "/api/ranking":
            _json_response(self, load_ranking())

        elif path == "/api/recommendations":
            _json_response(self, {"memo": load_memo()})

        else:
            _json_response(self, {"error": "Not found"}, 404)

    def log_message(self, *args):
        pass  # suppress default request logging
