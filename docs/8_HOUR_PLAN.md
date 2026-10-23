# Hackathon: 8-hour critical path

Date: **Saturday, 24 October 2026** (according to submitted proposal). This is a delivery order, not a promise that no failures can occur.

| Event clock | Priority | Outcome / exit criterion |
|---|---|---|
| 00:00–00:30 | P0 | Confirm competition rules. Create repo/environment; open demo UI and confirm versions |
| 00:30–01:15 | P0 | Install Chromium and local axe-core; run actual browser smoke test |
| 01:15–02:15 | P0 | Establish 3 deterministic fixture findings; verify every target and source selector |
| 02:15–03:15 | P0 | Patch proposal + exact diff + explicit reject and approve controls |
| 03:15–04:15 | P0 | Write to working copy; rescan; regression and browser-error rollback |
| 04:15–05:00 | P1 | Polish labels, status messages, manual-review queue, download files |
| 05:00–05:45 | P2 | Connect real Gemini API only if P0 stable; test failure fallback |
| 05:45–06:45 | P0 | Run full test matrix, test on second laptop/browser, clean repo |
| 06:45–07:30 | P1 | Practice 3-minute live demo, rehearse failure response and judge Q&A |
| 07:30–08:00 | P0 | Freeze code, run one final smoke test, keep baseline backup for emergency |

## The most important pre-event tasks (22–23 October)

1. Confirm hackathon policy on reuse or pre-building code.
2. Install Python 3.11+, Node LTS and npm; test `setup_mac.sh` on the *actual demo laptop*.
3. Run `python -m pytest -q` and **`python -m accessloop.smoke`** with all dependencies online.
4. Open Streamlit, fix the seeded three issues, and download the final JSON report.
5. Set up the free-tier Gemini key if allowed and desired. Never depend on it for the core workflow.
6. Screenshot/screen-record successful stages (only as a fallback if live Wi-Fi fails). Explain transparently when a fallback is shown.
7. Rehearse rejection, approval, failure handling and truthful claims. Decide who speaks/operates.

## Go / no-go

- **GO** if initial axe findings exist, the three supported repairs pass rescan, rejection changes no files, and rollback has been tested.
- **WARN** if Gemini is down: use deterministic mode and label it honestly.
- **NO-GO** if the browser scan does not run or an approval can change the source without verified evidence. Fix these before UI polish.

## Team split, if both registered teammates attend

**Developer 1:** scanner, patch engine, rollback and tests. **Developer 2:** Streamlit UI, walkthrough, evidence and integration. Integrate every hour. One owner signs off on all workspace writes and tests.
