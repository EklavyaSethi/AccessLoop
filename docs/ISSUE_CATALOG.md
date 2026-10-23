# AccessLoop issue catalogue

Generated from the real axe-core engine (version 4.14.0) and the 55 WCAG 2.2 Level A and AA success criteria. Regenerate with `python -m accessloop.catalog`.

> **Scope note.** No list can contain every possible accessibility barrier, because usability for real people is not a finite checklist. This catalogue is complete against the two standards that matter for compliance work: every rule the axe engine can detect, and every WCAG 2.2 A/AA criterion. Where a tool cannot test a criterion, it is listed as manual-only rather than left out.

## 1. Summary

- axe rules in the engine: **105**. Run by AccessLoop today: **63**. Not run: **42**.
- Handling today: **85** with a live human-approved fix, **0** planned deterministic fixes, **0** planned reviewer-assisted fixes, **4** guidance-only, **16** excluded (deprecated, experimental or AAA).
- WCAG 2.2 A + AA criteria: **55**. At least partly testable by axe: **23**. Not testable by axe at all: **32**, of which **10** could get an AccessLoop-built browser or site check.
- **Best-practice checks (optional):** 26 more rules (heading order, landmarks, skip link, empty headings and more) run when "Include best-practice checks" is turned on. Auditors usually report these; they are off by default because they are not WCAG failures.
- axe "needs review" results (where the engine cannot decide) are listed too, and many of them can be fixed and re-verified the same way.

## 2. How AccessLoop handles each rule

| Handling | Meaning |
|---|---|
| `live` | Fix available now (human-approved) |
| `auto` | Planned: deterministic fix |
| `assisted` | Planned: fix with reviewer input |
| `guided` | Detected: guidance only, no edit |
| `excluded` | Not scanned: reason given |

Priority: **P1** = most common real-world failures (WebAIM top six) and banking-form needs; **P2** = next.

## 3. Live fixes (human-approved) (85)

| Rule | WCAG | Level | Priority | Scanned today | What AccessLoop does |
|---|---|---|---|---|---|
| `accesskeys` | - | best-practice | P2 | no | Fixed with your approval.  |
| `area-alt` | 2.4.4, 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies alt text for image-map areas. |
| `aria-allowed-attr` | 4.1.2 | A | P2 | yes | Fixed with your approval.  |
| `aria-allowed-role` | - | best-practice | P2 | no | Fixed with your approval.  |
| `aria-braille-equivalent` | 4.1.2 | A | P2 | yes | Fixed with your approval.  |
| `aria-command-name` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies an accessible name (aria-label) for the control. |
| `aria-conditional-attr` | 4.1.2 | A | P2 | yes | Fixed with your approval.  |
| `aria-deprecated-role` | 4.1.2 | A | P2 | yes | Fixed with your approval.  |
| `aria-dialog-name` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a dialog name (aria-label / aria-labelledby). |
| `aria-hidden-body` | 1.3.1, 4.1.2 | A | P2 | yes | Fixed with your approval. Remove aria-hidden from &lt;body&gt;. |
| `aria-hidden-focus` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it.  |
| `aria-input-field-name` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies an accessible name for the custom input. |
| `aria-meter-name` | 1.1.1 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a name for the meter. |
| `aria-progressbar-name` | 1.1.1 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a name for the progress bar. |
| `aria-prohibited-attr` | 4.1.2 | A | P2 | yes | Fixed with your approval.  |
| `aria-required-attr` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it.  |
| `aria-required-children` | 1.3.1 | A | P2 | yes | Fixed with your approval.  |
| `aria-required-parent` | 1.3.1 | A | P2 | yes | Fixed with your approval.  |
| `aria-roles` | 4.1.2 | A | P2 | yes | Fixed with your approval.  |
| `aria-tab-name` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a name for the tab. |
| `aria-text` | - | best-practice | P2 | no | Fixed with your approval.  |
| `aria-toggle-field-name` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a name for the toggle. |
| `aria-tooltip-name` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a name for the tooltip. |
| `aria-treeitem-name` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a name for the tree item. |
| `aria-valid-attr` | 4.1.2 | A | P2 | yes | Fixed with your approval.  |
| `aria-valid-attr-value` | 4.1.2 | A | P2 | yes | Fixed automatically when the page makes the answer clear, otherwise you type it.  |
| `autocomplete-valid` | 1.3.5 | AA | P1 | yes | Fixed with the text you type; AccessLoop never guesses it. Suggest a valid autocomplete token from the field type/name (KYC forms); reviewer confirms. |
| `avoid-inline-spacing` | 1.4.12 | AA | P2 | yes | Fixed with your approval.  |
| `blink` | 2.2.2 | A | P2 | yes | Fixed with your approval. Unwrap the deprecated &lt;blink&gt; element, keeping its text. |
| `button-name` | 4.1.2 | A | P1 | yes | Fixed automatically when the page makes the answer clear, otherwise you type it. Un-hides visible button text wrongly marked aria-hidden. Icon-only buttons are escalated to a human. |
| `bypass` | 2.4.1 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Insert a "Skip to main content" link and target; reviewer confirms placement. |
| `color-contrast` | 1.4.3 | AA | P1 | yes | Fixed automatically when the page makes the answer clear, otherwise you type it. Compute the nearest colour of the same hue that reaches 4.5:1 (3:1 for large text); reviewer approves the CSS change. |
| `definition-list` | 1.3.1 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it.  |
| `dlitem` | 1.3.1 | A | P2 | yes | Fixed with your approval.  |
| `document-title` | 2.4.2 | A | P1 | yes | Fixed with the text you type; AccessLoop never guesses it. Propose a &lt;title&gt; from the page heading; reviewer edits and approves. |
| `duplicate-id-aria` | 4.1.2 | A | P2 | yes | Fixed with your approval.  |
| `empty-heading` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it.  |
| `empty-table-header` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it.  |
| `form-field-multiple-labels` | 3.3.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it.  |
| `frame-title` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a title for the frame. |
| `frame-title-unique` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it.  |
| `heading-order` | - | best-practice | P2 | no | Fixed with your approval.  |
| `html-has-lang` | 3.1.1 | A | P1 | yes | Fixed with your approval. Adds lang="&lt;reviewer-chosen code&gt;" to &lt;html&gt;. |
| `html-lang-valid` | 3.1.1 | A | P1 | yes | Fixed with the text you type; AccessLoop never guesses it. Replace an invalid lang value with a reviewer-chosen code. |
| `html-xml-lang-mismatch` | 3.1.1 | A | P2 | yes | Fixed with your approval. Make xml:lang match the lang attribute. |
| `image-alt` | 1.1.1 | A | P1 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer marks the image decorative (alt="") or supplies alt text; AI may suggest wording. |
| `image-redundant-alt` | - | best-practice | P2 | no | Fixed with your approval.  |
| `input-button-name` | 4.1.2 | A | P1 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a value/label for the button input. |
| `input-image-alt` | 1.1.1, 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies alt text for the image button. |
| `label` | 4.1.2 | A | P1 | yes | Fixed automatically when the page makes the answer clear, otherwise you type it. Links an immediately adjacent visible &lt;label&gt; to its unique &lt;input&gt; with for=. Other label layouts are planned. |
| `label-content-name-mismatch` | 2.5.3 | A | P2 | yes | Fixed with your approval. Align the accessible name with the visible text; reviewer approves. |
| `label-title-only` | - | best-practice | P2 | no | Fixed with your approval. Replace a title-only label with a real &lt;label&gt;; reviewer approves. |
| `landmark-banner-is-top-level` | - | best-practice | P2 | no | Fixed with your approval.  |
| `landmark-contentinfo-is-top-level` | - | best-practice | P2 | no | Fixed with your approval.  |
| `landmark-no-duplicate-banner` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it.  |
| `landmark-no-duplicate-contentinfo` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it.  |
| `landmark-no-duplicate-main` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it.  |
| `landmark-one-main` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it.  |
| `landmark-unique` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it.  |
| `link-in-text-block` | 1.4.1 | A | P2 | yes | Fixed with your approval. Add an underline (or other non-colour cue) to in-text links via CSS; reviewer approves. |
| `link-name` | 2.4.4, 4.1.2 | A | P1 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies link text (aria-label) or marks it for rewrite. |
| `list` | 1.3.1 | A | P2 | yes | Fixed with your approval.  |
| `listitem` | 1.3.1 | A | P2 | yes | Fixed with your approval.  |
| `marquee` | 2.2.2 | A | P2 | yes | Fixed with your approval. Unwrap the deprecated &lt;marquee&gt; element, keeping its text. |
| `meta-refresh` | 2.2.1 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it.  |
| `meta-viewport` | 1.4.4 | AA | P1 | yes | Fixed with your approval. Remove user-scalable=no and restrictive maximum-scale so users can zoom. |
| `meta-viewport-large` | - | best-practice | P2 | no | Fixed with your approval. Raise or remove maximum-scale values below 5. |
| `object-alt` | 1.1.1 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies alternative text for the &lt;object&gt;. |
| `page-has-heading-one` | - | best-practice | P2 | no | Fixed with the text you type; AccessLoop never guesses it.  |
| `presentation-role-conflict` | - | best-practice | P2 | no | Fixed with your approval.  |
| `role-img-alt` | 1.1.1 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies alt text for the role="img" element. |
| `scope-attr-valid` | - | best-practice | P2 | no | Fixed with your approval. Remove invalid scope values from table cells. |
| `scrollable-region-focusable` | 2.1.1, 2.1.3 | A | P2 | yes | Fixed with your approval. Add tabindex="0" so keyboard users can scroll the region. |
| `select-name` | 4.1.2 | A | P1 | yes | Fixed automatically when the page makes the answer clear, otherwise you type it. Link an adjacent &lt;label&gt; or add an aria-label supplied by the reviewer. |
| `server-side-image-map` | 2.1.1 | A | P2 | yes | Fixed with your approval.  |
| `skip-link` | - | best-practice | P2 | no | Fixed with your approval. Fix the skip link target; reviewer confirms. |
| `summary-name` | 4.1.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies visible text for the &lt;summary&gt;. |
| `svg-img-alt` | 1.1.1 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it. Reviewer supplies a name (&lt;title&gt;/aria-label) for the SVG image. |
| `tabindex` | - | best-practice | P2 | no | Fixed with your approval. Replace positive tabindex values with 0 or remove them; reviewer checks the resulting tab order. |
| `table-duplicate-name` | - | best-practice | P2 | no | Fixed with your approval.  |
| `target-size` | 2.5.8 | AA | P2 | yes | Fixed with your approval.  |
| `td-headers-attr` | 1.3.1 | A | P2 | yes | Fixed with your approval.  |
| `th-has-data-cells` | 1.3.1 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it.  |
| `valid-lang` | 3.1.2 | AA | P1 | yes | Fixed with the text you type; AccessLoop never guesses it. Replace an invalid lang on a page section with a reviewer-chosen code. |
| `video-caption` | 1.2.2 | A | P2 | yes | Fixed with the text you type; AccessLoop never guesses it.  |

## 4. Planned: deterministic fixes (0)

| Rule | WCAG | Level | Priority | Scanned today | What AccessLoop does |
|---|---|---|---|---|---|

## 5. Planned: reviewer-assisted fixes (0)

| Rule | WCAG | Level | Priority | Scanned today | What AccessLoop does |
|---|---|---|---|---|---|

## 6. Guidance only (4)

Needs a structure, design or content decision that a template cannot make safely, so AccessLoop reports it with the axe guidance link and does not edit it.

| Rule | WCAG | Level | Scanned today |
|---|---|---|---|
| `landmark-main-is-top-level` | - | best-practice | no |
| `nested-interactive` | 4.1.2 | A | yes |
| `no-autoplay-audio` | 1.4.2 | A | yes |
| `region` | - | best-practice | no |

## 7. Excluded from scanning (16)

| Rule | Reason |
|---|---|
| `aria-roledescription` | Deprecated by axe. |
| `audio-caption` | Deprecated by axe. |
| `color-contrast-enhanced` | Level AAA only; outside the WCAG AA target. |
| `css-orientation-lock` | Experimental in axe (off by default). |
| `duplicate-id` | Deprecated by axe (WCAG 4.1.1 Parsing was removed in WCAG 2.2). |
| `duplicate-id-active` | Deprecated by axe (WCAG 4.1.1 Parsing was removed in WCAG 2.2). |
| `focus-order-semantics` | Experimental in axe (off by default). |
| `frame-focusable-content` | Not applicable: AccessLoop never loads frame contents (every network request is blocked during a scan), so the frame's inner controls cannot be checked here. |
| `frame-tested` | Switched off: AccessLoop never loads frame contents (every network request is blocked during a scan), so this "was the frame tested?" check would always ask for review. |
| `hidden-content` | Experimental in axe (off by default). |
| `identical-links-same-purpose` | Level AAA only; outside the WCAG AA target. |
| `landmark-complementary-is-top-level` | Deprecated by axe. |
| `meta-refresh-no-exceptions` | Level AAA only; outside the WCAG AA target. |
| `p-as-heading` | Experimental in axe (off by default). |
| `table-fake-caption` | Experimental in axe (off by default). |
| `td-has-header` | Experimental in axe (off by default). |

## 8. All 55 WCAG 2.2 A + AA criteria

| Criterion | Name | Level | axe rules | Next step | Why it matters for BFSI |
|---|---|---|---|---|---|
| 1.1.1 | Non-text Content | A | `aria-meter-name`, `aria-progressbar-name`, `image-alt`, `input-image-alt`, `object-alt`, `role-img-alt`, `svg-img-alt` | Partly testable by axe; manual checks still needed. |  |
| 1.2.1 | Audio-only and Video-only (Prerecorded) | A | `audio-caption` | Partly testable by axe; manual checks still needed. |  |
| 1.2.2 | Captions (Prerecorded) | A | `video-caption` | Partly testable by axe; manual checks still needed. |  |
| 1.2.3 | Audio Description or Media Alternative (Prerecorded) | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 1.3.1 | Info and Relationships | A | `aria-hidden-body`, `aria-required-children`, `aria-required-parent`, `definition-list`, `dlitem`, `list`, `listitem`, `p-as-heading`, `table-fake-caption`, `td-has-header`, `td-headers-attr`, `th-has-data-cells` | Partly testable by axe; manual checks still needed. |  |
| 1.3.2 | Meaningful Sequence | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 1.3.3 | Sensory Characteristics | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 1.4.1 | Use of Color | A | `link-in-text-block` | Partly testable by axe; manual checks still needed. |  |
| 1.4.2 | Audio Control | A | `no-autoplay-audio` | Partly testable by axe; manual checks still needed. |  |
| 2.1.1 | Keyboard | A | `frame-focusable-content`, `scrollable-region-focusable`, `server-side-image-map` | Partly testable by axe; manual checks still needed. |  |
| 2.1.2 | No Keyboard Trap | A | **none (manual-only)** | Tab through the page and flag any element focus cannot leave. |  |
| 2.1.4 | Character Key Shortcuts | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 2.2.1 | Timing Adjustable | A | `meta-refresh` | Partly testable by axe; manual checks still needed. | Banking sessions time out; users need warning and a way to extend. |
| 2.2.2 | Pause, Stop, Hide | A | `blink`, `marquee` | Partly testable by axe; manual checks still needed. |  |
| 2.3.1 | Three Flashes or Below Threshold | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 2.4.1 | Bypass Blocks | A | `bypass` | Partly testable by axe; manual checks still needed. |  |
| 2.4.2 | Page Titled | A | `document-title` | Partly testable by axe; manual checks still needed. |  |
| 2.4.3 | Focus Order | A | **none (manual-only)** | Record the Tab order and show it for human review. |  |
| 2.4.4 | Link Purpose (In Context) | A | `area-alt`, `link-name` | Partly testable by axe; manual checks still needed. |  |
| 2.5.1 | Pointer Gestures | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 2.5.2 | Pointer Cancellation | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 2.5.3 | Label in Name | A | `label-content-name-mismatch` | Partly testable by axe; manual checks still needed. |  |
| 2.5.4 | Motion Actuation | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 3.1.1 | Language of Page | A | `html-has-lang`, `html-lang-valid`, `html-xml-lang-mismatch` | Partly testable by axe; manual checks still needed. |  |
| 3.2.1 | On Focus | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 3.2.2 | On Input | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 3.2.6 | Consistent Help | A | **none (manual-only)** | In whole-site mode, check help links appear in the same place on every page. |  |
| 3.3.1 | Error Identification | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. | Form errors on KYC, payments and claims must be identified in text. |
| 3.3.2 | Labels or Instructions | A | `form-field-multiple-labels` | Partly testable by axe; manual checks still needed. | Every field on an application form needs a visible label or instruction. |
| 3.3.7 | Redundant Entry | A | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. | Do not make users re-enter information already given in the same process. |
| 4.1.2 | Name, Role, Value | A | `area-alt`, `aria-allowed-attr`, `aria-braille-equivalent`, `aria-command-name`, `aria-conditional-attr`, `aria-deprecated-role`, `aria-hidden-body`, `aria-hidden-focus`, `aria-input-field-name`, `aria-prohibited-attr`, `aria-required-attr`, `aria-roledescription`, `aria-roles`, `aria-tab-name`, `aria-toggle-field-name`, `aria-tooltip-name`, `aria-valid-attr`, `aria-valid-attr-value`, `button-name`, `duplicate-id-aria`, `frame-title`, `frame-title-unique`, `input-button-name`, `input-image-alt`, `label`, `link-name`, `nested-interactive`, `select-name`, `summary-name` | Partly testable by axe; manual checks still needed. |  |
| 1.2.4 | Captions (Live) | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 1.2.5 | Audio Description (Prerecorded) | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 1.3.4 | Orientation | AA | `css-orientation-lock` | Partly testable by axe; manual checks still needed. |  |
| 1.3.5 | Identify Input Purpose | AA | `autocomplete-valid` | Partly testable by axe; manual checks still needed. | KYC and sign-up forms: browsers and assistive tech can auto-fill name, address, phone and email. |
| 1.4.3 | Contrast (Minimum) | AA | `color-contrast` | Partly testable by axe; manual checks still needed. |  |
| 1.4.4 | Resize Text | AA | `meta-viewport` | Partly testable by axe; manual checks still needed. |  |
| 1.4.5 | Images of Text | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 1.4.10 | Reflow | AA | **none (manual-only)** | Render at 320 px width and flag horizontal scrolling. |  |
| 1.4.11 | Non-text Contrast | AA | **none (manual-only)** | Measure border and icon contrast of form controls against the 3:1 minimum. |  |
| 1.4.12 | Text Spacing | AA | `avoid-inline-spacing` | Partly testable by axe; manual checks still needed. |  |
| 1.4.13 | Content on Hover or Focus | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 2.4.5 | Multiple Ways | AA | **none (manual-only)** | In whole-site mode, check there is more than one way to find pages (navigation plus search or sitemap). |  |
| 2.4.6 | Headings and Labels | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 2.4.7 | Focus Visible | AA | **none (manual-only)** | Tab through the page and flag controls with no visible focus change. |  |
| 2.4.11 | Focus Not Obscured (Minimum) | AA | **none (manual-only)** | While tabbing, flag focused controls hidden behind sticky headers or footers. |  |
| 2.5.7 | Dragging Movements | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. |  |
| 2.5.8 | Target Size (Minimum) | AA | `target-size` | Partly testable by axe; manual checks still needed. |  |
| 3.1.2 | Language of Parts | AA | `valid-lang` | Partly testable by axe; manual checks still needed. |  |
| 3.2.3 | Consistent Navigation | AA | **none (manual-only)** | In whole-site mode, compare navigation order across pages. |  |
| 3.2.4 | Consistent Identification | AA | **none (manual-only)** | In whole-site mode, compare labels of repeated components across pages. |  |
| 3.3.3 | Error Suggestion | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. | Failed entries (account numbers, IFSC, PAN) need a suggested correction. |
| 3.3.4 | Error Prevention (Legal, Financial, Data) | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. | Financial and legal submissions must be reversible, checked or confirmed. |
| 3.3.8 | Accessible Authentication (Minimum) | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. | Login and OTP steps must not rely on memorising or transcribing codes with no alternative. |
| 4.1.3 | Status Messages | AA | **none (manual-only)** | Needs a human check; AccessLoop lists it in the manual checklist. | Transaction results and balance updates must be announced to screen readers. |

## 9. AccessLoop's own browser checks (beyond axe)

Run when "AccessLoop browser checks" is on. They test what axe cannot see in a single static render.

| Check | WCAG | Fix |
|---|---|---|
| `al-reflow`: Content must reflow at 320 CSS pixels without horizontal scrolling | 1.4.10 | automatic, human-approved |
| `al-text-spacing`: Text must not be cut off when users increase text spacing | 1.4.12 | automatic, human-approved |
| `al-focus-visible`: Keyboard focus must be visible | 2.4.7 | automatic, human-approved |
| `al-forced-colors`: Controls must stay visible in Windows high-contrast (forced colours) mode | 1.4.11 | guidance (needs a design decision) |

## 10. Best-practice rules (run when best-practice checks are on)

`accesskeys`, `aria-allowed-role`, `aria-dialog-name`, `aria-text`, `aria-treeitem-name`, `empty-heading`, `empty-table-header`, `heading-order`, `image-redundant-alt`, `label-title-only`, `landmark-banner-is-top-level`, `landmark-contentinfo-is-top-level`, `landmark-main-is-top-level`, `landmark-no-duplicate-banner`, `landmark-no-duplicate-contentinfo`, `landmark-no-duplicate-main`, `landmark-one-main`, `landmark-unique`, `meta-viewport-large`, `page-has-heading-one`, `presentation-role-conflict`, `region`, `scope-attr-valid`, `skip-link`, `tabindex`, `table-duplicate-name`

---
Automated tools cannot certify WCAG conformance; keyboard, screen-reader and human usability testing remain necessary.
