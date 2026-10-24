# Measurements

Produced by `python -m accessloop.measure` (rule-based drafts) and `python -m accessloop.measure --ai` (AI drafts). Re-run them on your own machine; numbers depend on hardware.

## Rule-based drafts (no AI)

Machine: linux, Python 3.13.16. AI: off (rule-based). Scan: WCAG A/AA plus best-practice rules. Agent policy: low risk only (default).

| Measure | Result |
|---|---|
| Sample pages measured (+ refused as unsafe, by design) | 12 (+ 1) |
| Violation nodes: before → after agent → after drafts applied | 155 → 118 → 100 |
| Fixes kept by the agent (each verified by a re-scan) / rolled back | 35 / 0 |
| Fixes handed to a person (need words) | 61 |
| Drafts produced / verified when applied exactly as drafted | 17 / 17 (100%) |
| Scan + agent time per page (median) | 0.95 s |
| Throughput (scan + agent, one process) | 48.9 pages per minute |
| Agent time per verified fix | 0.28 s |

| Page | Violations before → after agent → after drafts | Fixes kept | Drafts verified | Seconds |
|---|---|---|---|---|
| 01_kyc_onboarding.html | 6 → 0 → 0 | 6 | 0/0 | 1.8 |
| 02_sip_signup.html | 6 → 3 → 0 | 3 | 3/3 | 2.0 |
| 03_loan_emi_calculator.html | 4 → 1 → 0 | 3 | 1/1 | 0.99 |
| 04_insurance_claim.html | 5 → 0 → 0 | 5 | 0/0 | 1.36 |
| 05_banking_edge_cases.html | 8 → 5 → 0 | 3 | 5/5 | 2.59 |
| 06_accessible_login.html | 0 → 0 → 0 | 0 | 0/0 | 0.36 |
| 08_legacy_portal_gallery.html | 22 → 15 → 8 | 7 | 7/7 | 5.48 |
| 09_netbanking_structure_gallery.html | 76 → 68 → 66 | 6 | 1/1 | 4.39 |
| 10_no_landmarks_notice.html | 3 → 3 → 3 | 0 | 0/0 | 0.34 |
| 11_widgets_gallery.html | 23 → 21 → 21 | 2 | 0/0 | 1.17 |
| 12_responsive_focus_gallery.html | 0 → 0 → 0 | 0 | 0/0 | 0.31 |
| 13_statement_layout.html | 2 → 2 → 2 | 0 | 0/0 | 0.33 |

A draft that verifies passed the engine's checks (the problem is gone, nothing else got worse). Whether it is the right description still needs a person, which is why AccessLoop never applies drafts on its own.
