# Jev Classification Prompt — v1

Model: `jev-1.14.0`
Label config: `jev-1.14.0+classify-v1`

## Questions

### topic (choice)
**Instructions**: What is the primary topic of this Spotify app review?

| Choice | Criteria |
|---|---|
| access | Login, signup, password, or account access problems |
| usability | Navigation, controls, layout, queue/playlist management, ad interruptions |
| playback | Playback failure, crashes, lag, audio quality, connection failures |
| downloads | Downloading, saved music, offline listening, disappearing downloads |
| catalog | Missing songs/artists, search/discovery, recommendations, lyrics |
| billing | Price, charges, subscriptions, paywalls, premium entitlement |
| support | Contacting support and the support response quality |
| other | General praise/criticism, unrelated content, no specific topic |

### intent (choice)
**Instructions**: What is the intent? Apply precedence: cancellation > complaint > request > praise > unclear

| Choice | Criteria |
|---|---|
| cancellation | Explicitly leaving, uninstalling, cancelling, or threatening to do so |
| complaint | Negative experience or mixed praise/criticism with a reported problem |
| request | Desired change or feature without reporting a failure |
| praise | Positive review with no complaint or request |
| unclear | Unrelated content, bare slogans, or meaningless text |

### severity (choice)
**Instructions**: Rate the severity of the problem reported (1=no problem, 5=serious harm). Choose only one.

| Choice | Criteria |
|---|---|
| 1 | No reported problem: praise, neutral/unclear content, or a pure feature request |
| 2 | Dislike, generic criticism, minor annoyance, or cosmetic issue; no functional loss |
| 3 | A degraded or restricted function; some use or workaround remains |
| 4 | A clearly blocked core task (cannot log in or play music) |
| 5 | Explicit serious financial, privacy, or data harm |

### sentiment (score, 0.0–4.0 → normalized to -1.0–1.0)
**Instructions**: Rate the overall sentiment of this review from very negative to very positive

Scale:
0 = Very negative — angry, hostile, or strongly dissatisfied
1 = Negative — disappointed or dissatisfied
2 = Neutral — factual, mixed, or unclear
3 = Positive — satisfied or pleased
4 = Very positive — enthusiastic, delighted, or highly satisfied

Normalization: `sentiment = (score / 2.0) - 1.0`

### needs_review (noul, float 0.0–1.0 → bool)
**Instructions**: Should this review be flagged for human review due to ambiguity, missing context, or unusual content?

Threshold: `needs_review = noul_score > 0.5`
