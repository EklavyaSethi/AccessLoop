# Test matrix and release checklist (v0.13)

| ID | Scenario | Expected | Automation |
|---|---|---|---|
| T01 | Scan each sample page | Real axe findings and needs-review items | `test_samples_real`, smoke |
| T02 | Every one of the 85 fix templates | Applied on a real page, verified, nothing else rises | `sample_suite` (proven count printed) |
| T03 | Fix needs words only a person knows | No guessed text; reviewer types it, or it stays open | `test_workflow`, `test_streamlit_ui` |
| T04 | Reject, or approve without consent | No write; identical SHA-256 | `test_workflow` |
| T05 | Stale proposal after another edit | Blocked | `test_workflow` |
| T06 | Fix makes another rule worse / element still fails / scan crashes | Byte-identical rollback | `test_workflow`, `test_fixers` |
| T07 | Batch of identical fixes | All applied, re-verified as one decision | `test_workflow` |
| T08 | Undo one kept fix | Later fixes replayed and re-verified | `test_workflow` |
| T09 | Four-eyes | Maker cannot confirm own change; approver role needed | `test_web`, `test_accounts` |
| T10 | Audit log tampering, forged signature | Detected | `test_ledger`, `test_accounts` |
| T11 | Scripts, handlers, javascript: URLs, srcdoc | Refused (strict) or stripped and never run (scripts mode) | `test_validator` |
| T12 | Input over 2 MB, request body over 3 MB | Refused | `test_validator`, `test_web` |
| T13 | Random malformed HTML (400 seeded documents) | Editor never corrupts text outside the edit | `test_fuzz` |
| T14 | Template mapping | Fix carried into the template; re-rendered template re-scanned | `test_templates` |
| T15 | Exports: patch, signed evidence, ACR, Jira, GitHub, JUnit, SARIF | Valid files | `test_cli`, `test_web` |
| T16 | Optional AI advice | Off by default; consent + redaction; never writes | `test_ai` |
| T17 | AccessLoop's own UIs | No serious/critical violations in any state | `test_selfcheck`, `python -m accessloop.selfcheck` |
| T18 | Streamlit app (real runtime) | Every page runs under AppTest; Hindi interface renders | `test_streamlit_ui` |
| T20 | Agent mode | Applies only what its policy allows, verifies each change, never types text, stops at limit/circuit breaker, approver-only in four-eyes | `test_agent`, sample suite B15 |
| T21 | AI drafts | Consent per run, redacted context, invalid output dropped, labelled rule-based fallback, accepted/edited logged, key never leaked | `test_ai_drafts` |
| T22 | "Where is this on the page?" | Sentence, breadcrumb and source lines for the exact element | `test_context` |
| T23 | Captions written in the app; Reject | Valid WebVTT file created and linked; rejected fixes never re-offered or applied by the agent | `test_captions`, `test_reject` |
| T24 | Value of a run (ROI) | Measured vs assumed figures, assumptions validated, no saving claimed when nothing was fixed | `test_roi` |
| T25 | Licences, setup and container files | Apache-2.0 present, no GPL/AGPL dependency, setup scripts and Docker files present, port local-only | `test_licenses`, `python -m accessloop.licenses` |
| T26 | Clean install on Linux, Windows and Docker | Setup script runs the full tests and smoke test; Docker image smoke-tested as non-root and served | `.github/workflows/platforms.yml` |
| T27 | Speed and draft quality on the samples | Throughput, time per fix, drafts verified when applied as-is | `python -m accessloop.measure` (see `docs/MEASUREMENTS.md`) |
| T19 | Keyboard-only use, 200% zoom, screen reader pass | Manual | Before every demo |

## Run before showing judges

```bash
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pytest -q
python -m accessloop.smoke
python -m accessloop.selfcheck
python -m accessloop.sample_suite
python -m accessloop.licenses
python -m accessloop.measure          # optional: speed and draft numbers for the deck
streamlit run app.py
```

## Acceptance criteria

1. Zero writes without approval; zero changes to original files.
2. Every kept fix: target fell, no other rule rose, the element passes.
3. Every rollback restores the exact previous bytes.
4. Every unhandled issue appears in the manual queue; nothing is silently dropped.
5. No "WCAG compliant" claim anywhere in the product or the pitch.
