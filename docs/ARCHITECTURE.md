# Architecture and trust boundaries (v0.10)

## Pipeline

```
HTML page (2 MB max) · or a .zip of a site · or a server-side template + JSON context
            |
   Validator: strict mode (no scripts, handlers, active URLs)  |  scripts mode (trusted pages; scripts never run)
            |
   Safe scan copy: scripts / base / on* / srcdoc / active URLs stripped, CSP meta added,
   assets served from the page's own folder, every network request and navigation blocked and recorded
            |
   Chromium (Playwright) + axe-core 4.14  (+ optional AccessLoop browser checks: focus visible on Tab,
   forced colours, 320 px reflow, text spacing)
            |
   Findings (violations) + "needs review" items, each tied to the exact source element (data-al-uid)
            |
   85 deterministic fix templates  -> proposal: exact diff, risk, fields a person must type
            |                         (optional AI advice: off by default, consent + redaction, never writes)
   PREVIEW (dry run: what a screen reader will hear before/after, nothing written)
            |
   EXPLICIT APPROVAL  (single, batch of identical fixes, or four-eyes: maker != checker)
            |
   Stale check (SHA-256) -> offset-based edit of the working copy (original never touched)
            |
   INDEPENDENT RE-SCAN
     - target rule count (violations + needs review) must fall
     - no other rule may rise
     - the specific element must no longer fail (element-level check)
           /            \
       VERIFIED       ROLLED BACK (byte-identical restore)
           |
   Hash-chained audit log, each entry signed with the reviewer's Ed25519 key when accounts are on
           |
   Exports: repaired HTML, git patch, signed evidence, ACR/VPAT-style report, Jira CSV, GitHub issues, JUnit, SARIF
```

## Components

| Module | Role |
|---|---|
| `scanner.py` | Persistent browser per thread, new isolated context per scan, axe injection, AccessLoop browser checks, screenshots |
| `htmlsource.py` | Tolerant HTML tokenizer with exact source offsets; edits never re-serialise the page |
| `fixers.py`, `fixers_extra.py` | 85 fix templates (auto, needs typed text, or mixed) |
| `agent.py` | Agent mode: perceive → plan → policy gate → act → verify → commit/rollback → re-plan → hand over |
| `verification.py` | Count gate + element-level gate + screen-reader announcement |
| `workflow.py` | State machine: load, scan, preview, approve, batch, revert, changes |
| `ledger.py`, `accounts.py` | Append-only hash chain; local accounts (scrypt passwords, encrypted Ed25519 keys), roles reviewer/approver/admin |
| `site.py`, `templates.py` | Many pages at once; carry verified fixes back into Jinja/Django/Thymeleaf/JSP/Handlebars templates |
| `exports.py`, `manual_tests.py` | Standard report formats; step-by-step checks for all 55 WCAG 2.2 A/AA criteria |
| `selfcheck.py`, `sbom.py` | AccessLoop scans its own UIs; CycloneDX bill of materials |
| `web/server.py` | Session used by both the local web UI and the Streamlit app |

## State contract

- `LOADED -> SCANNED`: real axe result, or a visible scan failure. Never a silent pass.
- `SCANNED -> PROPOSED`: only a registered template whose preconditions match the exact element.
- `PROPOSED -> REJECTED`: logged; no write.
- `PROPOSED -> PENDING`: four-eyes on; a second person with approver role must confirm.
- `PROPOSED -> VERIFIED | ROLLED_BACK`: decided only by the independent re-scan.
- `VERIFIED -> REVERTED`: a person can undo any single kept fix; later fixes are replayed and re-verified.

## What the agent decides, and what it never decides

The agent picks eligible findings, builds the exact edit, previews it, applies it after approval, observes the re-scan and
commits or rolls back. It abstains when the right words are unknowable (it asks for typed text instead of guessing). No
language model writes files or decides verification; optional AI advice is advisory only.

## Security and scope

- Page scripts never run in the scanner or preview. All network access from the page is blocked and listed.
- Per-user workspaces, deleted after 24 h (`ACCESSLOOP_WORKSPACE_TTL_HOURS`). Original files are never modified.
- Local accounts are SSO-ready (identity is a pluggable object) but SSO itself is not implemented or tested.
- Supported inputs: static HTML, rendered pages of server-side templates, and template sources (Jinja rendered by
  AccessLoop; other engines with a rendered sample). React/Angular/Vue component sources are on the roadmap.

## Verification limits

Automated rules cover part of WCAG. A clean scan is not conformance. The WCAG manual checklist page covers all 55 A/AA
criteria with steps; its results feed the ACR report.
