# Topic Definitions, Severity Scale, and Entity Keywords

## 8 Topics

| Topic | Definition | Example Keywords |
|---|---|---|
| `access` | Login, signup, password, or account access problems | login, sign in, password, account, logout |
| `usability` | Navigation, controls, layout, queue/playlist management, ad interruptions | ad, shuffle, queue, playlist, interface, skip |
| `playback` | Playback failure, crashes, lag, connection failures, audio quality | play, crash, audio, lag, freeze, buffer |
| `downloads` | Downloading, saved music, offline listening, disappearing downloads | download, offline, saved, storage |
| `catalog` | Missing songs/artists, search/discovery, recommendations, lyrics | lyric, search, recommendation, artist, song |
| `billing` | Price, charges, subscriptions, paywalls, premium entitlement | premium, subscription, payment, charge, price |
| `support` | Contacting support and the support response quality | support, customer service, help, contact |
| `other` | General praise/criticism, unrelated content, no specific topic | — |

## Severity Scale (1–5)

| Level | Meaning |
|---|---|
| 1 | No reported problem: praise, neutral/unclear, or pure feature request |
| 2 | Dislike, generic criticism, minor annoyance, or cosmetic issue; no functional loss |
| 3 | A degraded or restricted function; some use or workaround remains |
| 4 | A clearly blocked core task (cannot log in or play music) |
| 5 | Explicit serious financial, privacy, or data harm |

## Intent Precedence

`cancellation` > `complaint` > `request` > `praise` > `unclear`

- **cancellation**: Explicitly leaving, uninstalling, cancelling, or threatening to do so
- **complaint**: Negative experience or mixed praise/criticism with a reported problem
- **request**: Desired change or feature without reporting a failure
- **praise**: Positive review with no complaint or request
- **unclear**: Unrelated content, bare slogans, or meaningless text

## Notes on Edge Cases

- Mentioning a paid plan alone is NOT `billing`. A subscription failing to activate IS `billing`.
- Music crashing for a paying customer = `playback`, not `billing`.
- Bare boycott slogans = `unclear` unless there is a product complaint.
- Missing context should trigger `needs_review = true`.
- `cancellation` does not automatically raise severity.
