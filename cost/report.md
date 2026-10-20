# Cost Calculator Report

## Rates (as of 2026-10-19)

| Model | Input ($/MTok) | Output ($/MTok) |
|---|---|---|
| `jev-1.14.0` | $0.042 | $0.00 |
| `claude-haiku-4-5-20251001` | $0.80 | $4.00 |

## Pilot Run (cost_100.csv — 100 reviews)

| Metric | Cold Run | Warm Run (cache) |
|---|---|---|
| Reviews | 100 | 100 |
| Jev API calls | ~87 (13 cache hits) | 0 |
| Avg input tokens/call | ~350 | — |
| Avg output tokens/call | ~80 | — |
| Wall time (20 workers) | ~1 sec | <0.1 sec |
| Jev cost | ~$0.0013 | $0.00 |
| Haiku cost (group+memo) | ~$0.0057 | ~$0.0057 |
| **Total** | **~$0.0070** | **~$0.0057** |

## Full Run Projections

### Without deduplication (660,609 reviews, all classified)
- Jev calls: 660,609
- Input tokens: ~231 MTok (350 tok × 660,609)
- Jev cost: 231 × $0.042 = **~$9.70**
- Haiku (group + memo): ~$0.006
- **Total: ~$9.71**

### With deduplication (484,189 distinct texts)
- Jev calls: 484,189 (176,420 cache hits = 26.7% savings)
- Input tokens: ~169 MTok (350 tok × 484,189)
- Jev cost: 169 × $0.042 = **~$7.11**
- Haiku (group + memo): ~$0.006
- **Total: ~$7.12**
- **Savings: ~$2.59 (26.7% reduction)**

## Observed Actual Run Stats

### Phase 1 — v1 prompt (full 5-question, ~255 avg tokens)
- Jev calls: 539,704 (succeeded)
- Total input tokens: 137,686,124
- Avg input tokens/call: ~255
- Cost: **$5.78**

### Phase 2 — v3 prompt (intent-only, ~409 avg tokens)
- Jev calls: 292,112 (succeeded)
- Total input tokens: 119,519,575
- Avg input tokens/call: ~409
- Cost: **$5.02**
- Budget stopped at $4.97 limit; slight overshoot due to 30-second polling interval

### Phase 3 — Keyword fallback (no API calls)
- Records classified: 44,808
- Jev API calls: 0
- Cost: **$0.00**

### Cache Hit Rate
- 174,831 cache hits out of 660,622 records = 26.5%
- Fresh Jev calls: 485,778 (v1 + v3 combined)
- Keyword fallback: 44,808 records, $0 cost

### Verify (Stage 3)
- Jev calls: 201 (200 sample + 1 injection test)
- Input tokens: 80,664
- Cost: **$0.003**
- Topic agreement: 91.0%, Intent agreement: 93.0%, Severity MAE: 0.170

### Group + Memo (Haiku)
- group call: 271 input, 84 output tokens — cost ~$0.0005
- memo call: 596 input, 771 output tokens — cost ~$0.0034
- **Total Haiku: ~$0.004**

## Total Actual Cost

| Phase | Model | Cost |
|---|---|---|
| Phase 1 (v1 prompt) | jev-1.14.0 | $5.78 |
| Phase 2 (v3 prompt) | jev-1.14.0 | $5.02 |
| Phase 3 (keyword fallback) | keyword-v1 (local) | $0.00 |
| Verify (Stage 3) | jev-1.14.0 | $0.003 |
| Group + Memo (Stages 4, 6) | claude-haiku-4-5-20251001 | $0.004 |
| **Total** | | **~$10.81** |

## Token Usage (from calls.jsonl)

| Stage | Role | Model | Calls | Input Tok | Output Tok | Cost |
|---|---|---|---|---|---|---|
| Stage 2 (v1) | enrich | jev-1.14.0 | 539,704 | 137,686,124 | — | $5.78 |
| Stage 2 (v3) | enrich | jev-1.14.0 | 292,112 | 119,519,575 | — | $5.02 |
| Stage 2b (kw) | enrich | keyword-v1 | 44,808 | 0 | 0 | $0.00 |
| Stage 3 | verify | jev-1.14.0 | 201 | 80,664 | — | $0.003 |
| Stage 4 | group | claude-haiku-4-5-20251001 | 1 | 271 | 84 | ~$0.0005 |
| Stage 6 | memo | claude-haiku-4-5-20251001 | 1 | 596 | 771 | ~$0.0034 |

*Verify exact numbers with: `python3 cost/calculator.py --offline`*
