# Changelog

All notable changes to AccessLoop. Versions follow semantic versioning; dates are UTC.

## 0.13.1 – 2026-10-24
- `python -m accessloop.measure`: speed and draft quality on the sample pages (load, scan, agent, drafts applied exactly
  as drafted). Results in `docs/MEASUREMENTS.md`: 12 pages, 155 → 100 violations, 35 fixes kept and 0 rolled back,
  about 47 pages per minute, 0.3 s of agent time per verified fix; the deliberately unsafe sample is refused by design.
  `--ai` measures AI drafts (needs the AI key).
- New docs: `docs/API.md` (every HTTP endpoint, with an example), `docs/ADDING_A_FIX.md` (how to add a fix template).
  Updated: demo script, test matrix (T21–T27), architecture, how-it-works (85 templates, agent mode, AI drafts, SEBI
  deadline extended to 31 Oct 2026).

## 0.13.0 – 2026-10-24
- **Value of this run.** After every agent run, the agent page and the run report show the measured agent time and fixes
  next to an estimate of the same work done by hand: person-minutes and cost on this page, and per year for a chosen
  number of pages. Every figure is labelled **measured**, **assumption** or **estimate**; the assumptions (minutes to
  fix one issue by hand, to check one agent fix, to type one answer; developer cost per hour; pages per year) are modest
  defaults that anyone can replace with their organisation's own figures in the app ("Change the assumptions") or via
  `POST /api/roi`. Nothing fixed means no saving is claimed. The command line prints the same one-line summary.
  Rupee amounts use Indian digit grouping (₹4,41,740).

## 0.12.0 – 2026-10-24
- **Runs on Linux, Windows and Docker, not just macOS.** `setup_linux.sh` (with `--deps` for Chromium's system
  libraries), `setup_windows.cmd`/`setup_windows.ps1` (no execution-policy change, UTF-8 forced for the Hindi interface)
  and `start.sh`/`start_windows.cmd`. Every script installs the exact tested versions (`requirements.lock`,
  `package-lock.json`), then runs the tests and the real-browser smoke test.
- **Docker image** (`Dockerfile`, `docker-compose.yml`): two-stage build (axe-core via integrity-checked `npm ci`, no
  Node in the final image), runs as an unprivileged user, accounts/keys/workspaces on a `/data` volume, health check,
  port bound to localhost by default, AI optional (`--build-arg WITH_AI=0`), API key only from the shell.
- **New CI workflow "Install on every platform"**: runs the Linux and Windows setup scripts on clean GitHub machines
  (full tests + smoke test + an agent run from the command line on Windows), and builds the Docker image, smoke-tests
  inside it as the unprivileged user and checks the served app answers.
- **Licence: Apache-2.0** (`LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`). New `python -m accessloop.licenses` reads
  every pinned dependency's licence from its metadata; CI fails on GPL/AGPL/SSPL. axe-core and certifi (MPL-2.0) are
  used unmodified.
- Windows safety: `.gitattributes` keeps HTML, patches, captions and audit logs byte-exact on checkout; command-line
  outputs (templates, patches, audit logs) are written without newline translation. Empty AI settings (as Docker
  Compose passes them) now fall back to the defaults.
- `docs/DEPLOY.md`: every way to install and deploy, configuration variables, updating.

## 0.11.0 – 2026-10-24
- Fix (found by our own CI self-check): the "enter your name" notice used Streamlit's yellow warning box, whose text
  falls below the 4.5:1 contrast minimum. All warnings now use AccessLoop's own notice style (about 13:1).
- **Captions written in AccessLoop.** For a video without captions the reviewer can now type the captions in the app
  (one line per caption with its time, or paste a whole WebVTT/SRT file); AccessLoop validates them, creates a real
  WebVTT file next to the page (named after the video, e.g. `how-to-upi.en.vtt`), links it with `<track>`, and verifies
  the fix. New files a fix creates are recorded with their SHA-256 in the audit log, included in the git patch as new
  files, and downloadable with the repaired page as one zip. Pointing to an existing captions file still works.
- **Reject now visibly does something.** A rejected fix leaves the review list at once (nothing is written), is
  recorded in the audit log, appears in the Manual review queue as "Fix rejected by <name>", is never applied by the
  agent or a batch, and can be offered again from the queue.
- **"Where is this on the page?"** for every proposed fix, every agent question and every recorded decision: a plain
  sentence (what the element is, its label or text, the form, group or landmark it sits in and the section heading
  above it), a breadcrumb of its containers, the source code around it with line numbers and the changed lines marked,
  and on request a cropped picture of the element on the rendered page outlined in red. The sentence is also stored with
  each decision in the audit trail, evidence report and agent run report. Built for 1,000+ line files: the page is parsed
  once per version and only the neighbourhood of each fix is shown.
- **AI-drafted answers.** When the agent hands back fixes that need words (alt text, field and button names, link text,
  page titles), a language model (Google Gemini, or a local Ollama model) drafts them from redacted page context. Each
  draft fills the answer box with a badge (model, confidence, reason); a named person accepts or edits it; the fix is then
  verified or rolled back like any other. Model output is untrusted: drafts with markup, links, a wrong option or the
  wrong length are dropped. Consent is required per run; with AI off, unreachable or not consented, the agent offers
  rule-based suggestions from the page, labelled "no AI". The audit log records who drafted what (provider, model,
  redacted payload hash) and whether the person accepted, edited or skipped it. `python -m accessloop.ai_drafts` checks
  whether AI drafting works on this computer. Default Gemini model `gemini-3.8-flash`; if Google retires a model and
  names its replacement (HTTP 404), AccessLoop switches to the named model once and carries on. A busy model (503/429)
  is retried twice after short waits, then `GEMINI_FALLBACK_MODEL` is tried; the check command lists the models a key
  can use.
- **AI assistant panel** in the app sidebar: shows which AI drafts the answers (Gemini / local / off) and whether it is
  connected; switch provider, paste a Gemini key for this session (kept in memory only, never written to disk, logs or
  reports), set the model and run a one-click connection test with a sample draft. The agent page shows the same status.
- Fix: while the AI was drafting (a slow remote call), the agent held the session lock, so opening another page (for
  example Review fixes) froze the app until the model answered. The AI step now runs without the lock, every AI call
  has a time limit, and the whole AI step has a 25-second budget (ACCESSLOOP_AI_TIMEOUT), after which the agent falls
  back to labelled rule-based suggestions.
- **Agent run report.** One download (HTML that prints to PDF, plus signed JSON when signed in) with the policy and who
  approved it, page fingerprints before and after, the full console, every change with its exact text, rollbacks, what
  was handed to a person, how drafts were used, and the run's audit entries with hashes and chain status. On the agent
  page, the Reports page, `/api/export/agent-html|agent-json`, and written by `fix --agent` next to the output.

## 0.10.4 – 2026-10-23
- A named person is now mandatory for every decision and every agent run: approve, reject, batch, confirm, undo,
  manual-check results, answers to the agent and starting the agent are refused (HTTP 400 / CLI usage error) unless the
  user is signed in or has entered a real name (at least two characters, including a letter). The Streamlit app asks
  for the name in the sidebar and locks those buttons until it is given; `fix` on the command line needs `--reviewer`
  or `--user`. Scanning and reading reports still work without a name.

## 0.10.3 – 2026-10-23
- Fix: changes made by the agent showed empty before/after boxes in the audit trail and evidence report. Each agent
  write now records the exact text it changed (with line numbers for batches) and the elements it touched; the Issue
  coverage and home page numbers were also corrected (89 checks per scan, 4 guidance-only, 16 not run).

## 0.10.2 – 2026-10-23
- Agent console: a live terminal beside the step timeline shows exactly what the agent does, from real data: policy,
  sandbox and engine versions, scan counts per rule, plan split (allowed / needs words / held), each policy decision with
  line numbers, file fingerprints before and after every write, rule counts before and after every re-scan, audit entry
  hashes, rollbacks with the circuit-breaker count, and the hand-over. Saved with the run; also printed by `fix --agent`.
- Presentation pace (on by default in the app): a short pause after each step so an audience can follow. Pauses are left
  out of every reported time.

## 0.10.1 – 2026-10-23
- Self-check findings on the Streamlit app fixed: Streamlit's own sidebar menu nests section headers inside its list
  (axe list/listitem on every page), so it is hidden and replaced by plain grouped links; section headings are now
  <h2> (was <h3> straight after <h1>); caption text contrast raised; a stray role="list" removed from the agent trace.

## 0.10.0 – 2026-10-23
- **Agent mode**: one button (or `fix --agent`) and the agent repairs the page inside a policy you set: which risk levels
  it may apply alone, rules it must not touch, a change limit and a rollback circuit breaker. Every change is verified
  or undone; text is never guessed; questions and held fixes are handed back; the run and its policy are signed into
  the audit log. Live step timeline in the Streamlit app. In four-eyes mode only an approver can start it.
- Two more rule types fixed with the reviewer's decision: `landmark-no-duplicate-main` and `th-has-data-cells`
  (85 live). New sample page 13 and suite cases B14 (new rules) and B15 (agent mode): 18/18 cases, 88/88 templates.
- `pytest.ini` limits test collection to `tests/`.

## 0.9.0 – 2026-10-23
Closes every item in the October project audit (36 flaws). Highlights:
- Element-level verification on top of rule counts; a fix must clear its own element and no element may gain a problem.
- Screen-reader announcement before and after every fix, plus a dry-run preview before approving.
- Sandbox lists every blocked resource; one reused browser per worker (faster scans).
- AccessLoop browser checks: 320 px reflow, text spacing, forced colours and visible-focus checks.
- WCAG manual checklist for all 55 criteria, saved to the audit log and used by the conformance report.
- Exports: git patch, VPAT-style conformance report, Jira CSV, GitHub issues, JUnit XML, SARIF.
- Site scan with issues grouped by shared template; per-fix revert; visual before/after with highlights.
- Signed evidence (Ed25519), reviewer identities and optional four-eyes (maker-checker) approval.
- Local accounts with per-user workspaces and automatic clean-up; Hindi interface option.
- Template source mapping: fixes land in the template file (Jinja verified end to end; Django, Thymeleaf, JSP,
  Handlebars with a rendered sample).
- AI review off by default, consent per request, redaction, local-model option; data-flow note.
- Pinned dependencies, CycloneDX SBOM, pip-audit / npm audit in CI; seeded fuzz tests of the HTML editor.
- `python -m accessloop.selfcheck`: AccessLoop scans its own web UI and Streamlit app (no serious/critical issues).
- Validation report adds a do-no-harm line: 0 of 464 pages ended worse than they started.

## 0.8.0 – 2026-10-23
Validation on 464 third-party pages; batch approval; pages with scripts scanned without running them; agent trace.

## 0.7.0 – 2026-10-22
83 fixable rule types; best-practice and needs-review results; hash-chained audit log; CLI with SARIF.

## 0.6.0 – 2026-10-22
Position-based planner and reviewer-typed fixes (38 rule types).
