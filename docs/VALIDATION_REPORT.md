# AccessLoop validation report

Every number below is produced by `python -m accessloop.validation` followed by `python -m accessloop.validation_report`. All pages were written by third parties, not by the AccessLoop team. Each page went through the full loop: scan (WCAG A/AA + best-practice), propose, approve (a simulated reviewer approves everything and types neutral text where text is needed), re-scan, verify or roll back.

## Headline

- **464 pages and test cases**, **1066 approval decisions** covering **1685 individual fixes** (57 of the decisions were batches of similar fixes).
- Decisions verified: **1030** (97%), automatically rolled back: **32**, refused before writing: 4. Fixes kept: **1648**.
- Every original file was left untouched: **yes**. Every audit log hash chain verified: **yes**.
- Do no harm: pages that ended with more violations or more manual-review items than they started with: **0 of 464**. Every kept fix was checked to raise no other rule's count.
- Time per approval decision (write + full re-scan + verify): median **0.93 s**, 95th percentile **1.98 s**.

## 1. GOV.UK accessibility tool audit (142 known barriers)

Source: [alphagov/accessibility-tool-audit](https://github.com/alphagov/accessibility-tool-audit). Each page holds one deliberate barrier. GOV.UK published how 13 tools did on the same pages (results last updated April 2018, so those tools have improved since; treat the comparison as indicative). A barrier counts as detected when AccessLoop reports a rule on the page that it does not report on an identical control page without the barrier.

- AccessLoop detected **43 of 142** barriers (30%); 38 as violations, the rest as "needs review".
- Of the detected barriers, **40** had an AccessLoop fix proposal, and **38** were fully cleared after approval and re-verification.

| Tool | Barriers found (error) | Found or flagged for checking |
|---|---|---|
| **AccessLoop (axe-core 4.14 + best practice)** | **38** | **43** |
| SortSite | 57 | 57 |
| Tenon | 46 | 48 |
| axe (2017-18 run) | 41 | 43 |
| Siteimprove | 41 | 51 |
| FAE | 36 | 71 |
| Asqatasun | 35 | 67 |
| ASLint | 33 | 53 |
| HTML_CodeSniffer | 29 | 49 |
| AChecker | 29 | 49 |
| WAVE | 25 | 57 |
| EIII | 24 | 24 |
| Google ADT | 23 | 24 |
| Nu HTML Checker | 18 | 23 |

Barriers no automated tool can judge (plain language, meaningful sequence, focus order and similar) make up most of the misses; that is why AccessLoop keeps a manual checklist of the 32 WCAG criteria axe cannot test.

| Category | Detected / pages |
|---|---|
| Buttons | 3 / 4 |
| CSS | 0 / 5 |
| Colour and Contrast | 4 / 6 |
| Content | 1 / 5 |
| Forms | 9 / 19 |
| Frames | 1 / 2 |
| HTML | 3 / 11 |
| Headings | 2 / 4 |
| Images | 3 / 10 |
| Keyboard Access | 1 / 16 |
| Language of content | 1 / 9 |
| Links | 4 / 20 |
| Lists | 3 / 4 |
| Multimedia | 1 / 3 |
| Navigation | 1 / 1 |
| Page Layout | 1 / 1 |
| Page Title | 0 / 3 |
| Tables | 3 / 11 |
| Typography | 2 / 8 |

## 2. W3C ACT rules test cases (the official accessibility conformance test cases)

Source: [act-rules/act-rules.github.io](https://github.com/act-rules/act-rules.github.io), restricted to the 45 ACT rules that axe-core implements. "Failed" examples contain a real failure; "passed" examples are correct and must not be changed.

- Failed examples: **224**. Detected **209** (93%); fix proposed for **179**; failure fully removed and re-verified in **166** (79% of detected).
- Passed examples: **278**. Wrongly reported as a violation: **2** (1%). A fix was offered on **21**: 19 of those come from axe "needs review" results, where the engine itself is unsure and AccessLoop asks the reviewer instead of acting; the rest are the false alarms above. Nothing is ever applied without approval, and in this run no passed example was edited.
- Out of scope and not counted (AAA or experimental rules AccessLoop does not target): Audio element content has transcript, Audio element content is media alternative for text, Iframe with interactive elements is not excluded from tab-order, Links with identical accessible names have equivalent purpose, Meta element has no refresh delay (no exception), Orientation of the page is not restricted using CSS transforms, Text has enhanced contrast.

False alarms (all inherited from axe-core, listed for transparency): Meta element has no refresh delay - Passed Example 2; Visible label is part of accessible name - Passed Example 6

| ACT rule | Failed: detected / fixed / total | Passed: false alarms / total |
|---|---|---|
| ARIA attribute is defined in WAI-ARIA | 2 / 2 / 2 | 0 / 4 |
| ARIA required context role | 4 / 1 / 4 | 0 / 6 |
| ARIA required owned elements | 9 / 1 / 10 | 0 / 10 |
| ARIA state or property has valid value | 7 / 4 / 7 | 0 / 10 |
| ARIA state or property is permitted | 2 / 2 / 2 | 0 / 13 |
| Audio or video element avoids automatically playing audio | 0 / 0 / 2 | 0 / 3 |
| Autocomplete attribute has valid value | 10 / 10 / 10 | 0 / 8 |
| Block of repeated content is collapsible | 3 / 3 / 3 | 0 / 4 |
| Button has non-empty accessible name | 5 / 5 / 5 | 0 / 7 |
| Bypass Blocks of Repeated Content | 1 / 1 / 1 | 0 / 12 |
| Document has a landmark with non-repeated content | 3 / 2 / 3 | 0 / 4 |
| Document has an instrument to move focus to non-repeated content | 1 / 1 / 3 | 0 / 8 |
| Document has heading for non-repeated content | 2 / 2 / 4 | 0 / 9 |
| Element marked as decorative is not exposed | 3 / 2 / 3 | 0 / 6 |
| Element with aria-hidden has no content in sequential focus navigation | 6 / 5 / 6 | 0 / 6 |
| Element with lang attribute has valid language tag | 9 / 9 / 9 | 0 / 5 |
| Element with presentational children has no focusable content | 5 / 0 / 5 | 0 / 4 |
| Element with role attribute has required states and properties | 5 / 4 / 5 | 0 / 6 |
| Form field has non-empty accessible name | 9 / 6 / 9 | 0 / 9 |
| HTML page has lang attribute | 4 / 4 / 4 | 0 / 1 |
| HTML page has non-empty title | 6 / 5 / 6 | 0 / 5 |
| HTML page lang and xml:lang attributes have matching values | 2 / 2 / 2 | 0 / 3 |
| HTML page lang attribute has valid language tag | 4 / 4 / 4 | 0 / 2 |
| Headers attribute specified on a cell refers to cells in the same table element | 4 / 0 / 4 | 0 / 8 |
| Heading has non-empty accessible name | 8 / 5 / 8 | 0 / 5 |
| Id attribute value is unique | 3 / 3 / 3 | 0 / 4 |
| Iframe element has non-empty accessible name | 4 / 4 / 4 | 0 / 3 |
| Iframe elements with identical accessible names have equivalent purpose | 1 / 1 / 4 | 0 / 10 |
| Image button has non-empty accessible name | 3 / 3 / 3 | 0 / 4 |
| Image has non-empty accessible name | 5 / 5 / 5 | 0 / 8 |
| Important letter spacing in style attributes is wide enough | 4 / 4 / 4 | 0 / 6 |
| Important line height in style attributes is wide enough | 6 / 6 / 6 | 0 / 8 |
| Important word spacing in style attributes is wide enough | 4 / 4 / 4 | 0 / 6 |
| Link has non-empty accessible name | 11 / 11 / 11 | 0 / 11 |
| Menuitem has non-empty accessible name | 2 / 2 / 2 | 0 / 4 |
| Meta element has no refresh delay | 4 / 4 / 4 | 1 / 3 |
| Meta viewport allows for zoom | 5 / 2 / 7 | 0 / 5 |
| Object element rendering non-text content has non-empty accessible name | 5 / 5 / 6 | 0 / 4 |
| Role attribute has valid value | 2 / 2 / 2 | 0 / 3 |
| SVG element with explicit role has non-empty accessible name | 4 / 4 / 4 | 0 / 3 |
| Scrollable content can be reached with sequential focus navigation | 2 / 2 / 2 | 0 / 3 |
| Table header cell has assigned cells | 2 / 0 / 3 | 0 / 6 |
| Text has minimum contrast | 10 / 6 / 11 | 0 / 11 |
| Video element auditory content has accessible alternative | 2 / 2 / 2 | 0 / 2 |
| Visible label is part of accessible name | 16 / 16 / 16 | 1 / 16 |

## 3. MDN accessibility teaching pages

Source: [mdn/learning-area](https://github.com/mdn/learning-area) (`accessibility/`). 59 of 59 pages scanned.

- Violations: **286 → 13** (95% removed). Needs-review items: 22 → 19.
- Median scan time per page: 0.88 s.
- Most common items left (they need a person or a structural change): `region` (13).

## 4. Real-world Bootstrap templates

Source: 12 [StartBootstrap](https://github.com/StartBootstrap) templates. 39 of 39 pages scanned.

- Violations: **1013 → 68** (93% removed). Needs-review items: 319 → 295.
- Median scan time per page: 1.25 s.
- Most common items left (they need a person or a structural change): `region` (51), `color-contrast` (14), `label-title-only` (2), `page-has-heading-one` (1).

Note: these templates load Bootstrap from a CDN. AccessLoop never fetches anything from the internet during a scan, so CDN style sheets are absent and colour-contrast results reflect only the local styles.

## Rollbacks (the safety net working)

A rollback means the approved change did not make things better, or made something else worse, so the file was restored byte for byte. Most common rules and reasons:

- `color-contrast`: 15
- `landmark-one-main`: 4
- `aria-required-children`: 2
- `aria-required-parent`: 2
- `page-has-heading-one`: 2
- `aria-input-field-name`: 2
- `dlitem`: 1
- `bypass`: 1
- `aria-valid-attr-value`: 1
- `document-title`: 1

- Target rule color-contrast did not improve: 15
- Automated regression: 8
- Target rule landmark-one-main did not improve: 3
- Target rule aria-input-field-name did not improve: 2
- Target rule bypass did not improve: 1
- Target rule aria-valid-attr-value did not improve: 1

## Limits of this validation

- The reviewer is simulated. Real reviewers type meaningful text; the simulated one types neutral placeholder text, so some rollbacks (for example a typed name that does not match the visible label) would not happen with a careful reviewer.
- Scripts on these pages were not run (by design), so content built by JavaScript was not checked.
- Automated rules find only part of all barriers. Passing automated checks is not WCAG conformance.
