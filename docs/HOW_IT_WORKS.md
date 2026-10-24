# How AccessLoop works, in plain language

## The problem
Many websites cannot be used by people who are blind, have low vision, cannot use a mouse, or use a screen reader.
A common cause is small gaps in the page code: a form box with no label, an icon button with no name, a page that never says what language it is in.
Fixing these by hand across many pages is slow, and automatic "fix everything" tools are risky because they can change a page in ways nobody checked.
For a bank or insurer the risk is higher: a wrong change to a KYC or payment form is worse than the original problem.

## The idea: an inspector, a contractor and you
Think of renovating a building to make it wheelchair-friendly.

1. **The inspector (the scanner)** walks through the page in a real browser and writes down every barrier it can detect, with how serious each is. It uses axe-core, the industry-standard checking engine.
2. **The contractor (the planner)** finds the exact spot in the page code for each barrier and prepares a work order from a fixed template, not freely generated code. It has templates for 85 kinds of barrier. When the repair needs words only a person knows (what a photo shows, what an icon button does), the work order has a blank for you to fill in. It never invents those words.
3. **You, the site manager (the reviewer)** see each work order as a before/after comparison. Nothing is changed until you press Approve. You can also Reject.
4. **The re-inspection (verification)** happens right after every approved change. The inspector walks the page again. If the barrier is gone and nothing else got worse, the fix is marked verified.
5. **The undo button (rollback)** is automatic. If the barrier is still there, or any other problem count went up, the change is reverted and the page returns to exactly what it was.
6. **The paperwork (reports)** records every decision, who approved it, what changed, and fingerprints (SHA-256) of the file before and after. The log is append-only and each entry carries the fingerprint of the one before it, like a chain: change, remove or reorder any entry and the chain visibly breaks. Starting over (Reset) is written into the log, never used to erase it.

## What happens when you click through the app
1. **Load** a page (a sample, or your own HTML file). Your original is stored untouched.
2. **Scan.** The page opens in a locked-down browser: pages with scripts are refused by default (a trusted-page mode strips them and never runs them), and the browser may not fetch anything or navigate away. Problems are counted by severity. Optionally include "best-practice" checks (headings, landmarks, lists, tables). Items the engine cannot decide on are shown as "needs review".
3. **Review.** Each proposed repair appears as a card with a red/green diff and the line number. Fill in any blank, then Approve or Reject.
4. **Verify.** The app re-scans and tells you whether the fix passed or was rolled back.
5. **Report.** Download the evidence report (HTML, print to PDF), the JSON record, the repaired page, and the full issue catalogue.

Or let the **agent** do it: you set the rules once (for example "low-risk fixes only"), and it scans, fixes, re-checks and undoes on its own, then hands you only the questions that need your words. AI can draft those words (alt text, names, titles) for you to accept or edit. Afterwards it shows the **value of the run**: the agent's measured time next to an estimate of the same work by hand, with the assumptions visible and editable.

Problems the tool will not fix by itself appear in a **manual review queue** with a link to guidance, for example a photo that needs a description only a person can write.

## What it deliberately does not do
- It does not change anything without approval.
- It does not let AI write code. Optional AI only drafts words (alt text, names, titles) that a named person accepts or edits, and the engine then verifies them; it is off by default and needs consent each run.
- It does not guess. If the page language is not set, you choose it. If a button's purpose is ambiguous, it asks a human.
- It does not claim a page is "WCAG compliant". Automated checking finds only part of the real barriers.
- It is also a command-line tool for CI pipelines (`python -m accessloop scan site/ --format sarif`).
- It does not read or fix JavaScript framework sources (React, Angular, Vue) yet. It works on static HTML, rendered pages and server-side templates. Framework support is a roadmap item.
- Page code stays on your machine. The app runs locally (Mac, Linux, Windows or Docker) and does not send your HTML anywhere, except redacted snippets to the optional AI, with your consent, or to a model on your own computer.

## How complete is the issue list?
- The engine knows 105 rules. Every one is classified in `docs/ISSUE_CATALOG.md` as: fixed now, planned deterministic fix, planned fix with reviewer input, guidance only, or not scanned.
- A test fails if the engine ever adds a rule that nobody has classified, so the list cannot silently go stale.
- 63 WCAG rules run on every scan; 26 more best-practice rules run when you turn that option on.
- 85 rule types have a fix template, and the sample suite proves every one of them in a real browser. 4 need a structural decision and stay guidance-only; the rest are deprecated, experimental, AAA-only, or about frame contents the sandbox never loads.
- Of the 55 WCAG 2.2 Level A and AA criteria, 32 cannot be checked by any automatic tool and are listed as needing a human. No list can honestly promise to contain every possible barrier, but this one is complete against the engine's rules and the WCAG 2.2 A/AA criteria.

## Why this suits banking and insurance
Regulators expect accessible digital services: in India, SEBI's circular of 31 July 2025 requires regulated entities to audit and fix their digital platforms against IS 17802 / WCAG (the audit-and-remediation deadline was extended to 31 October 2026), and the EU Accessibility Act applies in Europe. Finance flows have extra requirements around error prevention and re-entering data. Reviewed, logged, reversible changes with an evidence report fit how regulated teams already work.
