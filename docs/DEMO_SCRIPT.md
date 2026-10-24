# 3-minute live demo (v0.13)

Before you start: `streamlit run app.py`, sign in, interface language English, browser zoom 100%.

## 0:00–0:20 — Pain point

"Scanners tell developers what is wrong. Someone still has to find the code, choose a fix, edit it and test again.
AccessLoop closes that loop, and nothing changes without a person's approval."

## 0:20–0:45 — Load and scan

**Load page** → sample *02 SIP signup* → **Scan**. Real Chromium + axe-core, scripts never run, network blocked.
Point at the metrics: violations, fixes ready, needs a human check.

## 0:45–1:25 — Agent mode (the headline)

Open **★ Agent mode**. Point at the policy: low-risk fixes only, never types text, stops after 6 rollbacks. Click
**Let the agent repair this page** and narrate the live timeline: perceive → policy check → act → verified (count
falls) → repeat. It ends by handing back questions: "these need words only a person knows", and the AI drafts them
(console lines marked `ai`; each answer box shows the model, confidence and reason). Accept one draft, edit another,
**Apply my answers**: verified, and the audit log records which draft was accepted and which was edited. Then
**Download agent run report**: one file with the policy, every step, every change and the audit hashes. Point at
**Value of this run**: measured agent time next to the same work by hand ("3 verified fixes in 0.7 s; about 1.2 h by
hand becomes 8 min of a person's time"). Say plainly that the minutes and rupee rate are adjustable assumptions; if a
judge offers their own figures, type them into "Change the assumptions" and press Recalculate.

## 1:25–1:50 — Human control and safety

On **Review fixes**, open one held fix: exact diff + **Preview what a screen reader will hear**. **Reject** it: the
audit log shows no write. Mention: any change that makes anything else worse is rolled back byte for byte, and in
four-eyes mode only an approver can start the agent.

## 1:50–2:20 — Evidence

**Verify results**: before/after by severity. **Reports**: git patch, signed evidence, ACR report, Jira CSV.
**Audit trail**: hash chain verified, decisions signed by the signed-in reviewer.

## 2:20–2:45 — Scale

**Site scan**: upload a .zip; identical problems grouped by shared template. Mention template mapping (Jinja etc.),
the CLI/CI with SARIF, the HTTP API, and that it installs with one command on Mac, Linux, Windows or Docker (all tested
on clean machines in CI). Apache-2.0.

## 2:45–3:00 — Proof and limits

"Validated on 464 third-party pages: 97% of approved decisions verified, MDN 286 → 13 violations, zero pages made worse.
It does not certify WCAG conformance; the manual checklist covers what tools cannot."

## Judge Q&A

- **Why agentic?** In agent mode it runs the whole loop itself: perceives (scan), plans, checks its policy, acts with a
  bounded tool, observes an independent re-scan, commits or rolls back, re-plans, and escalates what it must not decide.
  The policy is the human approval, given in advance and recorded.
- **Where is the AI?** The language model writes the words only a person could otherwise supply (alt text, names,
  titles); the agent's actions stay deterministic and every result is verified. AI drafts, a person approves, the engine
  proves. If the model is unreachable the agent says so and falls back to labelled rule-based suggestions.
- **Why not an LLM rewriting pages?** A plausible wrong label is worse than none. Templates are deterministic; AI is
  optional, advisory, consented and redacted.
- **How many issue types?** 85 axe rules fixed live, 4 guided, all 55 WCAG 2.2 A/AA criteria in the manual checklist.
- **Frameworks?** Static HTML, rendered pages, and server-side templates today; React/Angular/Vue sources on the roadmap.
- **Why now?** SEBI's 31 July 2025 circular requires regulated entities to audit and fix their digital platforms against
  IS 17802 / WCAG; the audit-and-remediation deadline was extended to 31 October 2026, a week after this event.
- **ROI numbers real?** Fixes, hand-overs and agent time are measured; minutes per manual fix and cost per hour are
  labelled, editable assumptions. On our 12 sample pages: 35 fixes kept, 0 rolled back, ~47 pages per minute
  (`docs/MEASUREMENTS.md`).
- **Same tool finds and checks?** Partly, and we say so: on top of axe we require the element itself to pass and show
  the screen-reader announcement; what tools cannot judge is the manual checklist and the approver's job.
- **Enterprise?** Local accounts with signed decisions, four-eyes, per-user workspaces, SBOM and dependency audit in CI.
  SSO is designed for, not yet built.
