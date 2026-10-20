# Golden 50 Evaluation Report

## Summary

- Evaluation set: 50 hand-labeled Spotify reviews
- Pipeline predictions sourced from: `records.jsonl` (completed records)
- Label configs used: mix of `jev-1.14.0+classify-v1`, `jev-1.14.0+classify-v3`, `keyword-v1`

| Metric | Value |
|---|---|
| Topic accuracy | 86.0% (43/50) |
| Intent accuracy | 86.0% (43/50) |
| Severity MAE | 0.240 |
| Total disagreements (topic or intent) | 13/50 |

## Disagreements (13 reviews)

### `292ce26a-815d-4bce-a3b6-93cb6c9e7e2c`
- Text: "Staff must be full of mentally ill kool-aid heads. Banning conservative music th..."
- Intent: gold=`unclear` → pred=`complaint` ❌

### `1fc8b08f-7d6a-472f-b317-8ceb28d00f22`
- Text: "Duo Premium .... No ads at all!..."
- Topic: gold=`billing` → pred=`usability` ❌

### `47428620-ec21-424d-a515-0b0b0012a5cf`
- Text: "This app is bad work..."
- Topic: gold=`other` → pred=`usability` ❌
- Severity: gold=2 → pred=3 (err=1)

### `fc344263-308d-48a1-9715-c380d063b6de`
- Text: "Great......"
- Intent: gold=`praise` → pred=`unclear` ❌

### `ac6cd66d-a9d2-42a4-afb8-2f84beff7fd1`
- Text: "Lhat ng song nasa spotify..."
- Topic: gold=`other` → pred=`catalog` ❌
- Intent: gold=`unclear` → pred=`request` ❌

### `46842184-32f8-4088-ac15-2a700a7e94ed`
- Text: "asem, lirik nya kdang gaada kek mana??..."
- Topic: gold=`catalog` → pred=`usability` ❌
- Severity: gold=2 → pred=3 (err=1)

### `5de7f95b-ccad-41b2-9f63-a13f7c1d9f09`
- Text: "We are boycotting Swedish app in our protest against Sweden for their desrecpect..."
- Intent: gold=`unclear` → pred=`cancellation` ❌
- Severity: gold=1 → pred=4 (err=3)

### `f4c8146a-d5c8-4168-b00e-21af666afc6a`
- Text: "Unconditional love, Stoli Canales..."
- Intent: gold=`unclear` → pred=`praise` ❌

### `3ddb3f4e-f7b9-430b-b335-eadc6d321f46`
- Text: "Deleting this App. The new update suck, we can't choose our fvrt songs after som..."
- Topic: gold=`usability` → pred=`billing` ❌

### `215463ae-95b7-4481-8747-1754b68f31fa`
- Text: "What is happening with Spotify?? Recently I'm trying to play a song but it doesn..."
- Intent: gold=`cancellation` → pred=`complaint` ❌
- Severity: gold=4 → pred=3 (err=1)

### `283b5843-a992-464f-b1dc-9dc7281ff390`
- Text: "Beth, we all got to give me a free dollar to go with 3 months, bro I can't be li..."
- Intent: gold=`unclear` → pred=`request` ❌

### `dceb14e7-2df0-422f-bb2b-73d7c373159a`
- Text: "I gave one star because I can't give any less than that. the new update is soooo..."
- Topic: gold=`usability` → pred=`playback` ❌

### `d2f3874f-d15d-4a2f-bb97-4f1213defa46`
- Text: "Too expensive and the free version is pretty much unusable with constant ads... ..."
- Topic: gold=`billing` → pred=`usability` ❌

## Analysis

Most disagreements fall into two patterns:

1. **Topic ambiguity** (7/13): Reviews span multiple topics (e.g. billing vs usability for subscription-related UI complaints). The keyword-based topic derivation picks the highest-keyword-count topic, which can differ from a human annotator's judgment on ambiguous texts.

2. **Intent ambiguity** (7/13): Short or ambiguous reviews (e.g. "5 stars" with no text context) led to `unclear` vs `praise` disagreements. The pipeline uses keyword matching for intent when not classified by Jev, which can miss subtle cues.

3. **Severity correlation**: MAE of 0.240 — severity is deterministically derived from intent in v3/keyword phases (complaint→3, cancellation→4, etc.), so severity errors track intent errors.

## Notes

- 14 of 50 reviews used `keyword-v1` (budget fallback) — these have lower expected accuracy
- 36 reviews used `jev-1.14.0` (v1 or v3) — higher expected accuracy
- The 86% topic/intent accuracy is consistent with the Stage 3 verify results (91% topic, 93% intent agreement on the broader 200-review sample using Jev-only classifications)
