# HTTP API

The local web server (`python -m accessloop.web`, default http://127.0.0.1:8765) exposes the same session layer the
Streamlit app uses (`accessloop/web/server.py`). Other tools, such as a bank's CI system or an internal portal, can
drive AccessLoop through it. For pipelines without a server, use the command line instead (`docs/CI.md`).

## Rules for every request

- **Local by default.** The server binds to 127.0.0.1 and only answers requests whose `Host` header it expects. To offer
  it to a team, put it behind the organisation's HTTPS reverse proxy and sign-in.
- **JSON in, JSON out.** `POST` bodies must be `Content-Type: application/json` and at most 3 MB. A cross-origin `Origin`
  header is refused.
- **A name is mandatory.** Every call that changes something (`approve`, `reject`, `revert`, `confirm`, `agent`, `draft`,
  `answer`, `manual`) needs `reviewer` (at least two characters, including a letter), or a signed-in account. It is
  recorded in the audit log.
- **The reply** to every successful `POST` is the full session state (the same object as `GET /api/state`). Errors return
  `{"error": "..."}` with a 4xx status.

## Read

| Method and path | Returns |
|---|---|
| `GET /healthz` | `ok` |
| `GET /api/state` | Session state: page, findings, proposals, fix log, audit status, agent run, AI drafts, value estimate (`roi`) |
| `GET /api/samples` | The sample pages that can be loaded by id |
| `GET /api/catalog` (`.csv`, `.md`) | Every axe rule and how AccessLoop handles it |
| `GET /api/report.html`, `GET /api/report.json` | Evidence report |
| `GET /api/export/<kind>` | `evidence`, `patch` (git patch, new files included), `acr` (VPAT-style report), `jira` (CSV), `github` (issues), `junit`, `agent-html`, `agent-json` (agent run report) and the repaired page |
| `GET /api/worksheet` | The WCAG manual checklist with its current results |
| `GET /api/screenshot/original.png`, `working.png` | Rendered screenshots |

## Act

| Method and path | Body | What it does |
|---|---|---|
| `POST /api/load` | `{"html": "...", "name": "page.html"}` or `{"sample": "examples/samples/02_sip_signup.html"}`; optional `"allow_scripts": true` (scripts are then stripped and never run) | Loads a page into a fresh workspace; the original is never modified |
| `POST /api/scan` | `{"language": "en", "best_practice": true, "extended": false}` | Real Chromium + axe-core scan; builds proposals |
| `POST /api/preview` | `{"id": "<proposal id>", "values": {...}}` | Dry run: the diff and what a screen reader will hear, nothing written |
| `POST /api/approve` | `{"id": "...", "reviewer": "A. Kumar", "values": {...}}` | Applies one fix, re-scans, keeps it or rolls it back |
| `POST /api/approve-batch` | `{"rule": "label", "reviewer": "..."}` | Applies all identical automatic fixes for one rule as one decision |
| `POST /api/reject` | `{"id": "...", "reviewer": "..."}` | Records the rejection; never offered again; nothing written |
| `POST /api/revert` | `{"n": 3, "reviewer": "..."}` | Undoes one kept fix; later fixes are replayed and re-verified |
| `POST /api/confirm` | `{"id": "...", "reviewer": "..."}` | Four-eyes: a second person with the approver role confirms a pending change |
| `POST /api/agent` | `{"risks": ["low"], "max_changes": 200, "deny_rules": [], "reviewer": "...", "ai_drafts": true, "ai_consent": true}` | Runs agent mode inside that policy; returns the run with every step |
| `POST /api/draft` | `{"consent": true, "reviewer": "..."}` | Drafts the words the agent asked for (AI if switched on and consented, else rule-based). Applies nothing |
| `POST /api/answer` | `{"answers": [{"rule": "image-alt", "selector": "img", "line": 12, "values": {"alt": "..."}}], "reviewer": "..."}` | Applies a person's answers through the normal approve path; logs whether each AI draft was accepted or edited |
| `POST /api/roi` | `{"assumptions": {"minutes_by_hand": 15, "cost_per_hour": 1500, "pages_per_year": 500}}` | Sets the organisation's own figures for the value estimate; `{}` restores the defaults |
| `POST /api/manual` | `{"criterion": "1.4.3", "result": "pass", "notes": "...", "reviewer": "..."}` | Records a manual WCAG check |
| `POST /api/login`, `/api/logout`, `/api/four-eyes` | account fields, or `{"on": true}` | Accounts and maker-checker mode |
| `POST /api/ai-review` | `{"consent": true}` | Optional AI second opinion on the current proposals (advisory only) |
| `POST /api/reset` | `{}` | Starts over; the reset itself is written to the audit log |

## Example: let the agent repair a page from a script

```bash
H='Content-Type: application/json'
curl -s -H "$H" -d '{"sample":"examples/samples/02_sip_signup.html"}' http://127.0.0.1:8765/api/load >/dev/null
curl -s -H "$H" -d '{"language":"en","best_practice":true}'           http://127.0.0.1:8765/api/scan >/dev/null
curl -s -H "$H" -d '{"risks":["low"],"reviewer":"Release bot (policy approved by A. Kumar)"}' \
     http://127.0.0.1:8765/api/agent | python -c "import json,sys; s=json.load(sys.stdin); print(s['agent']['applied'], 'fixes kept;', s['roi']['estimate']['percent_saved'], '% time saved (estimate)')"
curl -s http://127.0.0.1:8765/api/export/patch     > fixes.patch
curl -s http://127.0.0.1:8765/api/export/agent-html > agent_run_report.html
```
