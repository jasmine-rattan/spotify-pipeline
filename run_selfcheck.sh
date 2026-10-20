#!/bin/bash
# Run check_submission.py self-check after grading export
set -e
cd "$(dirname "$0")"

DATASET_DIR="Final Assignment - Spotify Reviews Dataset"
CSV_PATH="data/spotify_reviews_18months.csv"

echo "[Self-check] Building reference..."
.venv/bin/python3 "$DATASET_DIR/check_submission.py" reference \
    --full "$CSV_PATH" \
    --analysis "$CSV_PATH" \
    --out local-reference.json

echo "[Self-check] Running audit..."
.venv/bin/python3 "$DATASET_DIR/check_submission.py" check \
    --reference local-reference.json \
    --submission grading/ \
    --out self-check.json

echo "[Self-check] Result:"
.venv/bin/python3 -c "
import json
with open('self-check.json') as f:
    r = json.load(f)
print(f'Status: {r[\"status\"]}')
print(f'Coverage: {r[\"coverage\"]}')
if r.get('issue_counts'):
    print(f'Issues: {r[\"issue_counts\"]}')
if r.get('examples'):
    print(f'Examples: {r[\"examples\"][:3]}')
"
