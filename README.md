# AccessLoop · Reviewed accessibility repair

**Team OracleZero · AgentOps 2026 · Autonomous Workflow Automation · 24 October 2026**

A bounded, auditable tool that scans static HTML in a sandboxed Chromium with axe-core, proposes source-preserving fixes for **85 axe rule types** (every one proven in a real browser by the sample suite), applies only the ones a person approves, re-scans after every change, and rolls back anything that does not improve or that makes anything else worse. Text only a person can know (alt text, names, titles) is typed by the reviewer, never guessed. Every decision goes into an append-only, hash-chained audit log.

**This is a hackathon proof of concept, not a WCAG certification tool or production-hosted website repair service.**

> **New:** `streamlit run app.py` now opens a multi-page app (landing page plus a sidebar page for every operation, code in `streamlit_ui/`). A dependency-light local web UI (`python -m accessloop.web`) shares the same engine and is kept as a fallback. See `docs/HOW_IT_WORKS.md` for a plain-language explanation and `docs/ISSUE_CATALOG.md` for the full issue catalogue.

## Core demonstration

1. Select **Load seeded demo page**.
2. Select **Run accessibility scan**. Expect the seeded `html-has-lang`, `label`, and `button-name` findings to appear. For the full picture load `09_netbanking_structure_gallery.html` with **Include best-practice checks** on.
3. Open a diff. Select **Reject (no change)** and inspect the unchanged working-file hash in the audit trail.
4. Select **Approve and verify** on a proposal. It is written to the separate working copy **only after approval**, then rescanned.
5. Fix the remaining supported findings and inspect **verified** events, evidence JSON, and corrected HTML.
6. Load `examples/samples/05_banking_edge_cases.html` and type a link name that contradicts the visible text: the re-scan catches it and rolls it back.

## Setup (macOS, Linux, Windows or Docker)

You need **Python 3.11+**, **Node.js with npm**, and an internet connection during setup (Docker needs only Docker).
Each setup script installs the exact tested versions, the sandboxed Chromium and axe-core, then runs the tests and a
real-browser smoke test. All four are tested on clean machines in CI.

| System | Set up | Start |
|---|---|---|
| macOS | `bash setup_mac.sh` | `bash start.sh` |
| Linux | `bash setup_linux.sh --deps` | `bash start.sh` |
| Windows 10/11 | `setup_windows.cmd` | `start_windows.cmd` |
| Docker | `docker compose up --build` | (same command) |

Open http://localhost:8501. Details, options, configuration and server deployment: [docs/DEPLOY.md](docs/DEPLOY.md).
Drive it from other tools: [docs/API.md](docs/API.md). Add a fix type: [docs/ADDING_A_FIX.md](docs/ADDING_A_FIX.md).
Speed and draft-quality numbers: [docs/MEASUREMENTS.md](docs/MEASUREMENTS.md) (`python -m accessloop.measure`).

### Manual setup (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m playwright install chromium
npm ci --no-audit --no-fund
python -m pytest -q
python -m accessloop.smoke
streamlit run app.py
```

**Do not skip `python -m accessloop.smoke`:** it verifies the complete scanner → approval → patch → rescan workflow with the actual axe library. `npm install` caches axe-core locally; no external CDN is used during a scan.

### Optional genuine LLM review

```bash
python -m pip install -r requirements-ai.txt
export GEMINI_API_KEY='your_key_here'
# optional: export GEMINI_MODEL='gemini-3.8-flash'
streamlit run app.py
```

Choose **Optional: AI triage → Request AI review** after generating proposals. AI recommends or escalates a restricted patch, and explains why. It **cannot** generate arbitrary executable patches, alter the file, bypass human approval, or decide whether the axe rescan passed. Without an API key, the UI explicitly identifies the deterministic fallback. Only use synthetic, non-sensitive source snippets with the remote API. Never commit `.env` or credentials.

## What is supported?

- **Scanning:** axe-core WCAG 2.0/2.1/2.2 A + AA rules by default; tick **Include best-practice checks** (or `--best-practice`) for headings, landmarks, lists, tables and skip links. axe "needs review" results are listed too.
- **Fixing:** 85 rule types. Three kinds of fix:
  - *automatic* – everything needed is already on the page (link a visible label, un-hide button text, remove an invalid ARIA attribute, underline an in-text link, enlarge a tiny target, fix list structure);
  - *reviewer input* – the reviewer types or picks the missing words (alt text, link/button names, page title, which region is the main content);
  - *mixed* – automatic when the page makes the answer clear, otherwise it asks.
- **Guidance only (4 rules):** nested interactive controls, content outside landmarks, a nested main landmark, autoplaying audio. These need a structural decision.
- The full rule-by-rule list is `docs/ISSUE_CATALOG.md`.

Every applied fix is re-verified: the target rule must improve (violations plus needs-review items) and no other rule may get worse; otherwise the file is restored byte-for-byte.

- **Batch approval:** similar automatic fixes (for example 37 low-contrast labels) can be approved together. One write, one re-scan; the batch is kept only if every one of its fixes worked, otherwise it is rolled back and the fixes can be approved one by one.
- **Pages with scripts:** tick *Allow pages that contain scripts* (or `--allow-scripts`). Scripts, event handlers and active URLs are removed from the copy the browser scans and blocked by a Content-Security-Policy, so they never run; content that JavaScript would build is therefore not checked. The page's own style sheets, images and fonts are loaded from its folder (never from the internet).
- **Agent trace** (Streamlit sidebar → Evidence): the perceive → plan → human gate → act → verify → commit/rollback loop with counts, timings, every guardrail that acted, and the hash of every audit entry.
- **Where the AI is:** the agent's actions are deterministic and verified, because a plausible but wrong accessibility fix harms real users. A language model does the part only language can do: it **drafts the words** the agent needs from a person (alt text, names, titles) from redacted page context. A named person accepts or edits each draft, and the engine verifies the result. Switch on with `export ACCESSLOOP_AI=gemini GEMINI_API_KEY=…` (free key from Google AI Studio, `pip install -r requirements-ai.txt`) or `ACCESSLOOP_AI=local` for an Ollama model; check with `python -m accessloop.ai_drafts`. Without AI the agent offers rule-based suggestions, labelled "no AI".
- **Agent run report:** one HTML/JSON file per run with the policy, every step, every exact change, hand-overs and audit hashes.
- **A name on every decision (mandatory):** nothing can be approved, rejected, undone or run by the agent until the user is signed in or has entered their name; it is recorded with every audit entry and in the evidence report.
- **Agent mode** (sidebar → ★ Agent mode, or `python -m accessloop fix page.html --out fixed.html --agent --reviewer NAME`): the agent repairs the page within a policy you set (risk levels, rules off limits, change limit, circuit breaker), verifies every change, never guesses text, and hands back questions and held fixes. The run and its policy go into the audit log.
- **Preview before approval:** see the exact diff and what a screen reader will announce before and after, with nothing written.
- **Undo one fix** at any time; later fixes are replayed and re-verified.
- **Accounts and signed decisions (optional):** `python -m accessloop users add NAME --role approver`. Once an account exists, everyone signs in; every decision is signed with the reviewer's Ed25519 key, and *four-eyes* mode makes a second person (approver role) confirm each change. See `docs/ACCOUNTS.md`.
- **Site scan:** upload many pages or a .zip; identical problems across pages are grouped (usually one shared template) and automatic fixes can be applied to every page.
- **Server-side templates:** `python -m accessloop template page.jinja.html --context ctx.json` fixes the rendered page, carries each verified edit back into the template, re-renders and re-scans it. Works for Jinja directly; Django/Thymeleaf/JSP/Handlebars/ERB with a rendered sample (`--rendered`). React/Angular/Vue component sources are not supported yet.
- **AccessLoop browser checks** (`--extended`): focus visible when tabbing, forced-colours mode, 320 px reflow, WCAG text spacing.
- **WCAG manual checklist:** step-by-step checks for all 55 WCAG 2.2 A/AA criteria; results flow into the ACR report.
- **Exports:** repaired HTML, git patch, signed evidence, ACR/VPAT-style conformance report, Jira CSV, GitHub issues (`issues --create` via `gh`), JUnit XML, SARIF.
- **Optional AI advice:** off by default (`ACCESSLOOP_AI=gemini|local`), needs consent per page, sends a redacted snippet only, never writes. See `docs/DATA_FLOW.md`.
- **Interface language:** English or Hindi (navigation, page introductions, steps, buttons, key labels; machine-translated, native review pending). Findings stay in English.
- **Self-check:** `python -m accessloop.selfcheck` scans AccessLoop's own web UI and Streamlit app; both are currently free of serious and critical violations.
- **Validation:** `docs/VALIDATION_REPORT.md` – the full loop run over 464 third-party pages (GOV.UK accessibility tool audit, W3C ACT test cases, MDN, Bootstrap templates). Reproduce with `python -m accessloop.validation` + `python -m accessloop.validation_report`.

## Command line (CI-ready)

```bash
python -m accessloop scan site/ --format sarif --out a11y.sarif --fail-on serious   # exit 1 if serious/critical issues
python -m accessloop scan page.html --best-practice                                # readable summary with line numbers
python -m accessloop fix page.html --out fixed.html                                # asks before every change
python -m accessloop fix page.html --out fixed.html --approve-auto --reviewer "A. Rao"   # unattended: automatic fixes only
python -m accessloop audit verify fixed.audit.jsonl                                # detects any edit to the audit log
python -m accessloop audit verify-evidence evidence.json                           # checks a signed evidence file
python -m accessloop issues page.html --jira issues.csv                            # or --github / --create
python -m accessloop template form.jinja.html --context ctx.json --out form.fixed.jinja.html
```

Exit codes: 0 clean, 1 findings at or above `--fail-on`, 2 a page was refused or failed to scan, 64 usage error. See `docs/CI.md` for a GitHub Actions workflow that uploads SARIF to code scanning.

## Technical structure

```
app.py                        # Streamlit entry point (sidebar navigation)
streamlit_ui/                 # Streamlit pages: home, load, scan, review, verify, manual, checklist, preview, site, reports, audit, trace, coverage, how
accessloop/models.py          # typed findings / proposals / scan results
accessloop/scanner.py         # headless Chromium + locally-installed axe-core
accessloop/htmlsource.py      # single-pass HTML tokenizer: exact element offsets, comment/script aware
accessloop/fixers.py          # fix templates (names, labels, language, contrast, viewport, ARIA ...)
accessloop/fixers_extra.py    # fix templates (structure: lists, tables, landmarks, headings, media, spacing ...)
accessloop/planner.py         # maps each finding to its exact source element and builds the patch
accessloop/ledger.py          # append-only, hash-chained audit log
accessloop/cli.py             # command line: scan (text/JSON/SARIF), fix, audit verify
accessloop/ai_advisor.py      # optional, non-executing Gemini classification
accessloop/workflow.py        # workspace state, write controls, backups, event log
accessloop/verification.py    # target reduction and no-new-automated-issue gate
accessloop/smoke.py           # full browser integration test
accessloop/accounts.py        # local accounts, roles, Ed25519 signing keys
accessloop/site.py            # many pages / .zip, grouped by shared template
accessloop/templates.py       # carry verified fixes into server-side templates
accessloop/exports.py         # patch, ACR, Jira, GitHub, JUnit
accessloop/manual_tests.py    # 55-criterion WCAG manual checklist
accessloop/selfcheck.py       # AccessLoop scans its own interfaces
accessloop/sbom.py            # CycloneDX bill of materials
examples/                     # seeded and ambiguous HTML examples
examples/samples/             # 12 banking/insurance pages incl. three defect galleries (legacy portal, net-banking structure, investment widgets)
accessloop/sample_suite.py    # real-browser acceptance runner + report
tests/                        # independent engine tests
```

## Quality gates

- No file write on a rejected patch or missing approval.
- The original HTML is preserved separately from `working.html`.
- Proposal ID and SHA-256 bind the patch to the precise source version.
- Patch is regenerated from an allowlisted template before writing.
- Every successful write is immediately rescanned; no improvement / increased violations / scan failure triggers rollback.
- Files are written through temporary files and `os.replace` for atomic replacement.
- An append-only audit log (`audit.jsonl`) records every event with reviewer, rule, before/after, typed text and working-file hash; each entry carries the hash of the previous one, so edits, deletions and reordering are detected. Reset is recorded, never erased.
- Unrecognized or under-specified findings are escalated, not fabricated.
- HTML files under 2 MB. Scripts, inline event handlers, `srcdoc`, `<base>` and javascript:/vbscript:/active data: URLs are refused. During a scan every network request is blocked and any navigation (for example a meta refresh) is answered with 204 so the page cannot leave.

Not yet included: single sign-on, hosted multi-tenant deployment, React/Angular/Vue component sources, and testing with screen-reader users. Visual comparison (before/after screenshots) is shown to the reviewer but is not an automatic gate.

## Fast commands

```bash
python -m pytest -q                # all tests (engine, UIs, accounts, templates, fuzz)
python -m accessloop.smoke         # real axe + Chromium integration smoke test
python -m accessloop.selfcheck     # AccessLoop's own UIs, scanned for accessibility
python -m accessloop.sample_suite  # 16 real-browser acceptance cases -> sample_results/RESULTS.md (proves every fix template)
python -m accessloop.web           # fallback local web UI (http://127.0.0.1:8765), no extra install needed
python -m accessloop.catalog       # regenerate docs/ISSUE_CATALOG.md and data/issue_catalog.*
streamlit run app.py               # main multi-page Streamlit UI
```

See `docs/ARCHITECTURE.md`, `docs/DEMO_SCRIPT.md`, `docs/8_HOUR_PLAN.md`, and `docs/TEST_MATRIX.md` before the event.

## Hackathon rule check

Verify whether the event permits bringing prewritten starter code. If not, treat this package as a **pre-event rehearsal/reference** and implement according to the event's rules during the official build window.

## References

- [WebAIM Million 2026](https://webaim.org/projects/million/)
- [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [axe-core](https://github.com/dequelabs/axe-core)
- [Playwright for Python](https://playwright.dev/python/docs/intro)
- [Streamlit Session State](https://docs.streamlit.io/develop/concepts/architecture/session-state)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)

## Licence

Apache License 2.0: see [LICENSE](LICENSE) and [NOTICE](NOTICE). AccessLoop uses axe-core (MPL-2.0), Playwright,
Chromium, Streamlit and other open-source components unmodified; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
`python -m accessloop.licenses` lists every dependency's licence, and CI fails on any strong copyleft licence.
