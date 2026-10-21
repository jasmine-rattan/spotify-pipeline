// Pre-computed pipeline data — embedded at build time, no backend required

export const METRICS = {
  total: 660622,
  completed: 660609,
  quarantined: 13,
  cache_hits: 174831,
  topic_counts: {
    access: 9344,
    billing: 26771,
    catalog: 43505,
    downloads: 6435,
    other: 389093,
    playback: 43045,
    support: 2565,
    usability: 139851,
  },
  intent_counts: {
    cancellation: 25126,
    complaint: 255446,
    praise: 274939,
    request: 30464,
    unclear: 74634,
  },
}

export const RANKING = [
  { rank: "1", issue_id: "issue-usability", complaint_count: "102667", severity_sum: "299970", mean_severity: "2.921776", priority_score: "299970" },
  { rank: "2", issue_id: "issue-other",     complaint_count: "94837",  severity_sum: "261491", mean_severity: "2.757268", priority_score: "261491" },
  { rank: "3", issue_id: "issue-playback",  complaint_count: "32488",  severity_sum: "104399", mean_severity: "3.213463", priority_score: "104399" },
  { rank: "4", issue_id: "issue-catalog",   complaint_count: "19525",  severity_sum: "57812",  mean_severity: "2.960922", priority_score: "57812"  },
  { rank: "5", issue_id: "issue-billing",   complaint_count: "17443",  severity_sum: "52693",  mean_severity: "3.020868", priority_score: "52693"  },
  { rank: "6", issue_id: "issue-access",    complaint_count: "8390",   severity_sum: "27568",  mean_severity: "3.285816", priority_score: "27568"  },
  { rank: "7", issue_id: "issue-downloads", complaint_count: "4170",   severity_sum: "13245",  mean_severity: "3.176259", priority_score: "13245"  },
  { rank: "8", issue_id: "issue-support",   complaint_count: "1052",   severity_sum: "3123",   mean_severity: "2.968631", priority_score: "3123"   },
]

export const ISSUE_NAMES: Record<string, string> = {
  "issue-access":    "Login and Access Problems",
  "issue-billing":   "Pricing and Fraud Concerns",
  "issue-catalog":   "Missing or Unavailable Content",
  "issue-downloads": "Download and Offline Issues",
  "issue-other":     "General Complaints",
  "issue-playback":  "Audio Lag and Stuttering",
  "issue-support":   "Poor Customer Support",
  "issue-usability": "Ads and User Experience",
}

export const MEMO = `# PRODUCT MEMO: PRIORITY ISSUES FROM APP REVIEW ANALYSIS

**TO:** Product Leadership
**FROM:** Product Management
**RE:** Critical Issues Requiring Immediate Action
**SCOPE:** Analysis of 660,622 app reviews

---

## Executive Summary

Our review analysis has identified five major issue categories affecting user satisfaction. We recommend prioritizing fixes in a phased approach, starting with ads/UX and playback performance, which together account for ~137K complaints and represent the highest user frustration drivers.

---

## Top Priority Issues

**1. Ads and User Experience (URGENT)**

Ads remain our single largest pain point with 102,667 complaints (claim-001) and a severity sum of 299,970 (claim-002). The mean severity of 2.92 (claim-003) indicates moderate-to-high user frustration. This issue drives our highest priority score of 299,970 (claim-004).

*Recommendation:* Conduct immediate audit of ad placement algorithms and frequency caps.

**2. Audio Lag and Stuttering (HIGH)**

While complaint volume is lower at 32,488 (claim-009), this issue has the highest mean severity at 3.21 (claim-011), indicating severe user frustration. The priority score of 104,399 (claim-012) reflects that affected users are significantly more dissatisfied than average.

*Recommendation:* Escalate to engineering for investigation of buffer management and streaming optimization.

**3. General Complaints (MEDIUM-HIGH)**

The 94,837 complaints in this category (claim-005) with severity sum of 261,491 (claim-006) suggest systemic usability issues. Though mean severity is 2.76 (claim-007), the high volume warrants attention.

*Recommendation:* Conduct qualitative research to categorize these complaints and identify root causes in UX design.

**4. Pricing and Fraud Concerns (MEDIUM)**

17,443 complaints (claim-017) with a mean severity of 3.02 (claim-019) indicate serious trust issues around billing. The priority score of 52,693 (claim-020) suggests this drives churn among price-sensitive segments.

*Recommendation:* Audit billing transparency and fraud prevention measures.

**5. Missing/Unavailable Content (MEDIUM)**

19,525 complaints (claim-013) point to catalog gaps or technical issues accessing available music (claim-016). With mean severity of 2.96 (claim-015), this moderately impacts experience.

*Recommendation:* Analyze geographic content restrictions and error patterns with licensing partners.

---

## Recommended Action Plan

- **Phase 1 (Weeks 1-4):** Address ads/UX and playback issues
- **Phase 2 (Weeks 5-8):** Investigate general complaints and billing concerns
- **Phase 3 (Ongoing):** Monitor content availability`
