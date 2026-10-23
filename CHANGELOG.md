# Changelog

All notable changes to AccessLoop. Versions follow semantic versioning; dates are UTC.

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
