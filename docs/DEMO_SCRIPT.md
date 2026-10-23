# 3-minute live demo (v0.10)

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
falls) → repeat. It ends by handing back questions: "these need words only a person knows". Type one answer
(for example a field name), **Apply my answers**: verified.

## 1:25–1:50 — Human control and safety

On **Review fixes**, open one held fix: exact diff + **Preview what a screen reader will hear**. **Reject** it: the
audit log shows no write. Mention: any change that makes anything else worse is rolled back byte for byte, and in
four-eyes mode only an approver can start the agent.

## 1:50–2:20 — Evidence

**Verify results**: before/after by severity. **Reports**: git patch, signed evidence, ACR report, Jira CSV.
**Audit trail**: hash chain verified, decisions signed by the signed-in reviewer.

## 2:20–2:45 — Scale

**Site scan**: upload a .zip; identical problems grouped by shared template. Mention template mapping (Jinja etc.) and
the CLI/CI with SARIF.

## 2:45–3:00 — Proof and limits

"Validated on 464 third-party pages: 97% of approved decisions verified, MDN 286 → 13 violations, zero pages made worse.
It does not certify WCAG conformance; the manual checklist covers what tools cannot."

## Judge Q&A

- **Why agentic?** In agent mode it runs the whole loop itself: perceives (scan), plans, checks its policy, acts with a
  bounded tool, observes an independent re-scan, commits or rolls back, re-plans, and escalates what it must not decide.
  The policy is the human approval, given in advance and recorded.
- **Why not an LLM rewriting pages?** A plausible wrong label is worse than none. Templates are deterministic; AI is
  optional, advisory, consented and redacted.
- **How many issue types?** 85 axe rules fixed live, 4 guided, all 55 WCAG 2.2 A/AA criteria in the manual checklist.
- **Frameworks?** Static HTML, rendered pages, and server-side templates today; React/Angular/Vue sources on the roadmap.
- **Enterprise?** Local accounts with signed decisions, four-eyes, per-user workspaces, SBOM and dependency audit in CI.
  SSO is designed for, not yet built.
