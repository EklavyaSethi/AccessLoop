# AccessLoop sample-suite results

**18/18 cases passed** (real Chromium + axe-core, no fake scanner)

**Fix templates proven in a real browser: 88/88 rule types** (each applied, re-scanned and verified at least once).

## PASS - Starter demo (regression)
`examples/student_registration.html` - Original starter page: 3 seeded rules fixed end-to-end

- Baseline counts: `{'button-name': 1, 'html-has-lang': 1, 'label': 1}`  ->  Final counts: `{}`
- verified: **button-name** `#submit-registration`  `<span aria-hidden="true">Submit registration</span>` -> `<span>Submit registration</span>`
- verified: **html-has-lang** `html`  `<html>` -> `<html lang="en">`
- verified: **label** `#email`  `<label>University email</label>
    <input id="email" name="email" type="email" required>` -> `<label for="email">University email</label>
    <input id="email" name="email" type="email" required>`
  - [x] 3 seeded rules detected
  - [x] every applied patch verified
  - [x] seeded rules cleared
  - [x] original.html never modified

## PASS - Starter ambiguous icon (regression)
`examples/ambiguous_icon_button.html` - Icon-only button asks the reviewer, never guessed

- Baseline counts: `{'button-name': 1}`  ->  Final counts: `{'button-name': 1}`
- Manual-review queue: `button-name #icon-action`
  - [x] button-name detected
  - [x] no invented label: one input proposal, nothing written yet
  - [x] original.html never modified

## PASS - B1 KYC onboarding
`examples/samples/01_kyc_onboarding.html` - Many instances + reject / no-approval / stale guards on a KYC form

- Baseline counts: `{'button-name': 1, 'html-has-lang': 1, 'label': 4}`  ->  Final counts: `{}`
- verified: **button-name** `#submit-kyc`  `<span aria-hidden="true">Submit KYC details</span>` -> `<span>Submit KYC details</span>`
- verified: **html-has-lang** `html`  `<html>` -> `<html lang="en">`
- verified: **label** `#kyc-name`  `<label>Full name (as on PAN)</label>
    <input id="kyc-name" name="full_name" type="text">` -> `<label for="kyc-name">Full name (as on PAN)</label>
    <input id="kyc-name" name="full_name" type="text">`
- verified: **label** `#kyc-pan`  `<label>PAN number</label>
    <input id="kyc-pan" name="pan" type="text">` -> `<label for="kyc-pan">PAN number</label>
    <input id="kyc-pan" name="pan" type="text">`
- verified: **label** `#kyc-dob`  `<label>Date of birth</label>
    <input id="kyc-dob" name="dob" type="date">` -> `<label for="kyc-dob">Date of birth</label>
    <input id="kyc-dob" name="dob" type="date">`
- verified: **label** `#kyc-mobile`  `<label>Mobile number</label>
    <input id="kyc-mobile" name="mobile" type="tel">` -> `<label for="kyc-mobile">Mobile number</label>
    <input id="kyc-mobile" name="mobile" type="tel">`
  - [x] html-has-lang=1, label=4, button-name=1 detected
  - [x] 6 proposals generated
  - [x] reject leaves working file byte-identical
  - [x] approved=False leaves working file byte-identical
  - [x] stale proposal blocked
  - [x] 6 patches applied, all verified
  - [x] total violations reach 0
  - [x] original.html never modified

## PASS - B1b Invalid language
`examples/samples/01_kyc_onboarding.html` - Bad reviewer language input

- Baseline counts: `{'button-name': 1, 'html-has-lang': 1, 'label': 4}`  ->  Final counts: `{'button-name': 1, 'html-has-lang': 1, 'label': 4}`
- Manual-review queue: `button-name #submit-kyc`, `html-has-lang html`, `label #kyc-name`, `label #kyc-pan`, `label #kyc-dob`, `label #kyc-mobile`
- Note: Reviewer language "english" is not a BCP-47 code; agent abstains for that rule only.
  - [x] invalid language code -> no html-has-lang proposal
  - [x] other proposals still offered
  - [x] original.html never modified

## PASS - B2 SIP sign-up
`examples/samples/02_sip_signup.html` - Mixed: auto fixes plus three fixes that need reviewer-typed text

- Baseline counts: `{'html-has-lang': 1, 'image-alt': 1, 'label': 2, 'link-name': 1, 'select-name': 1}`  ->  Final counts: `{}`
- verified: **html-has-lang** `html`  `<html>` -> `<html lang="en">`
- verified: **image-alt** `img`  `<img src="banner-sip.png" width="480" height="100">` -> `alt="…"`
- verified: **label** `#sip-name`  `<label>Investor name</label>
    <input id="sip-name" name="investor" type="text">` -> `<label for="sip-name">Investor name</label>
    <input id="sip-name" name="investor" type="text">`
- verified: **label** `#sip-amount`  `<label>Monthly amount (₹)</label>
    <input id="sip-amount" name="amount" type="number" min="500">` -> `<label for="sip-amount">Monthly amount (₹)</label>
    <input id="sip-amount" name="amount" type="number" min="500">`
- verified: **link-name** `a`  `<a href="#risk">` -> `aria-label="…"`
- verified: **select-name** `#sip-fund`  `<select id="sip-fund" name="fund">` -> `aria-label="…"`
  - [x] language, labels, image, link and select problems detected
  - [x] alt text, link name and select name ask the reviewer (never guessed)
  - [x] input fix without typed text refused
  - [x] 6 patches, all verified
  - [x] total violations reach 0
  - [x] original.html never modified

## PASS - B3 Loan EMI calculator
`examples/samples/03_loan_emi_calculator.html` - Labels auto-fixed; icon-only reset button asks the reviewer

- Baseline counts: `{'button-name': 1, 'label': 3}`  ->  Final counts: `{}`
- verified: **button-name** `#emi-reset`  `<button id="emi-reset" type="reset">` -> `aria-label="…"`
- verified: **label** `#emi-amount`  `<label>Loan amount (₹)</label>
    <input id="emi-amount" name="principal" type="number" min="100000">` -> `<label for="emi-amount">Loan amount (₹)</label>
    <input id="emi-amount" name="principal" type="number" min="100000">`
- verified: **label** `#emi-rate`  `<label>Interest rate (% per year)</label>
    <input id="emi-rate" name="rate" type="number" step="0.05">` -> `<label for="emi-rate">Interest rate (% per year)</label>
    <input id="emi-rate" name="rate" type="number" step="0.05">`
- verified: **label** `#emi-tenure`  `<label>Tenure (months)</label>
    <input id="emi-tenure" name="tenure" type="number" min="12" max="360">` -> `<label for="emi-tenure">Tenure (months)</label>
    <input id="emi-tenure" name="tenure" type="number" min="12" max="360">`
  - [x] 3 labels and 1 button name detected
  - [x] icon-only reset button asks the reviewer instead of guessing
  - [x] all verified, violations reach 0
  - [x] original.html never modified

## PASS - B4 Insurance claim
`examples/samples/04_insurance_claim.html` - Claim form fully repaired and verified

- Baseline counts: `{'button-name': 1, 'html-has-lang': 1, 'label': 3}`  ->  Final counts: `{}`
- verified: **button-name** `#submit-claim`  `<span aria-hidden="true">Submit claim</span>` -> `<span>Submit claim</span>`
- verified: **html-has-lang** `html`  `<html>` -> `<html lang="en">`
- verified: **label** `#claim-policy`  `<label>Policy number</label>
    <input id="claim-policy" name="policy" type="text">` -> `<label for="claim-policy">Policy number</label>
    <input id="claim-policy" name="policy" type="text">`
- verified: **label** `#claim-date`  `<label>Date of incident</label>
    <input id="claim-date" name="incident_date" type="date">` -> `<label for="claim-date">Date of incident</label>
    <input id="claim-date" name="incident_date" type="date">`
- verified: **label** `#claim-amount`  `<label>Estimated claim amount (₹)</label>
    <input id="claim-amount" name="amount" type="number" min="0">` -> `<label for="claim-amount">Estimated claim amount (₹)</label>
    <input id="claim-amount" name="amount" type="number" min="0">`
  - [x] language, 3 labels, button name detected
  - [x] already-labelled textarea is not touched
  - [x] 5 patches applied, all verified
  - [x] total violations reach 0
  - [x] original.html never modified

## PASS - B5 Payment edge cases
`examples/samples/05_banking_edge_cases.html` - Near-miss patterns on a payment form: ask, never guess; contradicting typed text is rolled back

- Baseline counts: `{'button-name': 3, 'label': 4, 'link-name': 1}`  ->  Final counts: `{}`
- rolled_back: **link-name** `#stmt-link`  `<a href="/statements" id="stmt-link">` -> `aria-label="Download"`
- verified: **button-name** `#mystery`  `<button id="mystery" type="button">` -> `aria-label="…"`
- verified: **button-name** `button`  `<span aria-hidden="true">Pay now</span>` -> `<span>Pay now</span>`
- verified: **button-name** `#two-spans`  `<span aria-hidden="true">Confirm</span><span aria-hidden="true">transfer</span>` -> `<span>Confirm</span><span>transfer</span>`
- verified: **label** `#acct`  `<input id="acct" name="account" type="text">` -> `aria-label="…"`
- verified: **label** `input`  `<label>IFSC code</label>
    <input name="ifsc" type="text">` -> `<label for="al-ifsc-code">IFSC code</label>
    <input name="ifsc" type="text" id="al-ifsc-code">`
- verified: **label** `input`  `<input id="dup" name="amount" type="number">` -> `aria-label="…"`
- verified: **label** `input`  `<input id="dup" name="confirm_amount" type="number">` -> `aria-label="…"`
  - [x] label, button-name and link-name findings detected
  - [x] ambiguous patterns ask the reviewer; clear ones are auto
  - [x] typed name that contradicts the visible text is rolled back by the re-scan, file unchanged
  - [x] typed name that matches the visible text is verified
  - [x] every remaining fix verified
  - [x] total violations reach 0
  - [x] original.html never modified

## PASS - B8 Legacy portal gallery
`examples/samples/08_legacy_portal_gallery.html` - 22 defects across 20 rule types, all fixed and verified

- Baseline counts: `{'aria-roles': 1, 'aria-valid-attr': 1, 'autocomplete-valid': 1, 'button-name': 2, 'color-contrast': 1, 'document-title': 1, 'html-has-lang': 1, 'image-alt': 1, 'input-button-name': 1, 'input-image-alt': 1, 'label': 3, 'link-name': 1, 'marquee': 1, 'meta-viewport': 1, 'scrollable-region-focusable': 1, 'select-name': 1, 'summary-name': 1, 'svg-img-alt': 1, 'valid-lang': 1}`  ->  Final counts: `{}`
- verified: **aria-roles** `#fake-role`  `<div role="buton" id="fake-role">` -> `<div id="fake-role">`
- verified: **aria-valid-attr** `#typo-attr`  `<div aria-lable="Balance" id="typo-attr">` -> `<div id="typo-attr">`
- verified: **autocomplete-valid** `#reg-email`  `<input id="reg-email" name="email" type="email" autocomplete="fullname">` -> `autocomplete="…"`
- verified: **button-name** `#icon-only`  `<button id="icon-only" type="button">` -> `aria-label="…"`
- verified: **button-name** `#go`  `<span aria-hidden="true">Continue</span>` -> `<span>Continue</span>`
- verified: **color-contrast** `.muted`  `<p class="muted">` -> `<p class="muted" style="color: #747474 !important">`
- verified: **document-title** `html`  `<head>` -> `<title>…</title>`
- verified: **html-has-lang** `html`  `<html>` -> `<html lang="en">`
- verified: **image-alt** `img`  `<img src="rates-banner.png" width="400" height="80">` -> `alt="…"`
- verified: **input-button-name** `#clear`  `<input type="button" id="clear">` -> `aria-label="…"`
- verified: **input-image-alt** `input`  `<input type="image" src="go.png" width="24" height="24">` -> `alt="…"`
- verified: **label** `input`  `<label>Customer name</label>
    <input name="cust" type="text">` -> `<label for="al-customer-name">Customer name</label>
    <input name="cust" type="text" id="al-customer-name">`
- verified: **label** `#reg-email`  `<label>Registered email</label>
    <input id="reg-email" name="email" type="email" autocomplete="name">` -> `<label for="reg-email">Registered email</label>
    <input id="reg-email" name="email" type="email" autocomplete="name">`
- verified: **label** `#wrapped`  `<input id="wrapped" name="wrapped" type="text">` -> `aria-label="…"`
- verified: **link-name** `a`  `<a href="#statements">` -> `aria-label="…"`
- verified: **marquee** `marquee`  `<marquee>` -> `<div>`
- verified: **meta-viewport** `meta`  `<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">` -> `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
- verified: **scrollable-region-focusable** `.scroll`  `<div class="scroll">` -> `<div class="scroll" tabindex="0">`
- verified: **select-name** `#acct-type`  `<label>Account type</label>
    <select id="acct-type" name="type">` -> `<label for="acct-type">Account type</label>
    <select id="acct-type" name="type">`
- verified: **summary-name** `summary`  `<summary>` -> `aria-label="…"`
- verified: **svg-img-alt** `svg`  `<svg role="img" width="16" height="16">` -> `aria-label="…"`
- verified: **valid-lang** `span`  `<span lang="english">` -> `lang="…"`
  - [x] legacy portal has 20+ defects across 15+ rule types
  - [x] every finding gets a proposal
  - [x] every patch verified (none rolled back)
  - [x] total violations reach 0
  - [x] original.html never modified

## PASS - B9 Net-banking structure gallery
`examples/samples/09_netbanking_structure_gallery.html` - Best-practice + needs-review: 80+ problems across 35+ rule types, all fixed and verified

- Baseline counts: `{'accesskeys': 1, 'aria-allowed-role': 1, 'aria-conditional-attr': 1, 'aria-deprecated-role': 1, 'aria-hidden-focus': 1, 'aria-required-attr': 1, 'aria-required-children': 1, 'aria-required-parent': 1, 'aria-text': 1, 'aria-valid-attr-value': 1, 'avoid-inline-spacing': 1, 'definition-list': 1, 'dlitem': 2, 'empty-heading': 1, 'empty-table-header': 1, 'heading-order': 1, 'image-redundant-alt': 1, 'label-content-name-mismatch': 1, 'label-title-only': 2, 'label': 1, 'landmark-banner-is-top-level': 1, 'landmark-no-duplicate-banner': 1, 'landmark-no-duplicate-contentinfo': 1, 'landmark-one-main': 1, 'landmark-unique': 3, 'link-in-text-block': 1, 'list': 1, 'listitem': 3, 'meta-refresh': 1, 'object-alt': 1, 'page-has-heading-one': 1, 'presentation-role-conflict': 1, 'region': 31, 'scope-attr-valid': 1, 'table-duplicate-name': 1, 'target-size': 4, 'td-headers-attr': 1}`  ->  Final counts: `{'region': 1}`
- verified: **accesskeys** `span`  `<span accesskey="h">Home</span> <span accesskey="h">Help</span>` -> `<span accesskey="h">Home</span> <span>Help</span>`
- verified: **aria-allowed-role** `li`  `<li role="link">` -> `<li>`
- verified: **aria-conditional-attr** `#sms`  `<input type="checkbox" id="sms" aria-checked="true">` -> `<input type="checkbox" id="sms">`
- verified: **aria-deprecated-role** `ul`  `<ul role="directory">` -> `<ul role="list">`
- verified: **aria-hidden-focus** `.promo`  `<div aria-hidden="true" class="promo">` -> `aria-hidden … / tabindex="-1"`
- verified: **aria-required-attr** `div`  `<div role="checkbox" tabindex="0">` -> `aria-checked="…"`
- verified: **aria-required-children** `div`  `<div role="list"><span>Call 1800 000 000</span><span>Visit a branch</span></div>` -> `<div role="list"><span role="listitem">Call 1800 000 000</span><span role="listitem">Visit a branch</span></div>`
- verified: **aria-required-parent** `span`  `<span role="option">` -> `<span>`
- verified: **aria-text** `p`  `<p role="text">` -> `<p>`
- verified: **aria-valid-attr-value** `button`  `<button aria-expanded="yes" type="button">` -> `aria-expanded="…"`
- verified: **avoid-inline-spacing** `p`  `<p style="letter-spacing: 0.02em !important; line-height: 1.1 !important">` -> `<p style="letter-spacing: 0.02em; line-height: 1.1">`
- verified: **definition-list** `dl`  `<dl>
      <p>Charges are inclusive of GST.</p>
      <dt>NEFT</dt><dd>Free online</dd>
    </dl>` -> `<dt>/<dd>`
- verified: **dlitem** `dt`  `<dt>RTGS</dt><dd>Free online above ₹2 lakh</dd>` -> `<dt>RTGS</dt><dd>Free online above ₹2 lakh</dd></dl>`
- verified: **empty-heading** `h3`  `<h3></h3>` -> `<h3>…</h3>`
- verified: **empty-table-header** `th`  `<th></th>` -> `<th>…</th>`
- verified: **heading-order** `h4`  `<h4>` -> `<h4 aria-level="3">`
- verified: **image-redundant-alt** `img`  `<img src="logo.png" alt="Meridian Bank logo" width="40" height="40">` -> `<img src="logo.png" alt="" width="40" height="40">`
- verified: **label-content-name-mismatch** `button`  `<button aria-label="Submit profile update">` -> `<button>`
- verified: **label-title-only** `input`  `<input type="text" name="mobile" title="Mobile number">` -> `<input type="text" name="mobile" title="Mobile number" aria-label="Mobile number">`
- verified: **label** `input`  `<input type="text" name="acct" aria-describedby="acct-help">` -> `aria-label="…"`
- verified: **landmark-banner-is-top-level** `header`  `<header role="banner">` -> `<header>`
- verified: **landmark-no-duplicate-contentinfo** `footer`  `<footer>` -> `<section aria-label="…">`
- verified: **landmark-one-main** `html`  `<div class="content">` -> `role="main" / <main>`
- verified: **landmark-unique** `nav`  `<nav>` -> `aria-label="…"`
- verified: **link-in-text-block** `a`  `<a href="/rates" style="color:#2a5db0;text-decoration:none">` -> `<a href="/rates" style="color:#2a5db0; text-decoration: underline">`
- verified: **list** `ul`  `<ul>
      <div>Cheque book: free for the first 25 leaves</div>
      <li>Debit card: ₹250 a year</li>
    </ul>` -> `<ul>
      <li>Cheque book: free for the first 25 leaves</li>
      <li>Debit card: ₹250 a year</li>
    </ul>`
- verified: **listitem** `li`  `<li>Locker rent depends on locker size</li>` -> `<li>Locker rent depends on locker size</li></ul>`
- verified: **meta-refresh** `meta`  `<meta http-equiv="refresh" content="600; url=/logout">` -> `meta refresh …`
- verified: **object-alt** `object`  `<object data="statement-chart.svg" type="image/svg+xml" width="320" height="120">` -> `aria-label="…"`
- verified: **page-has-heading-one** `html`  `<div class="content" role="main">` -> `<h1>…</h1>`
- verified: **presentation-role-conflict** `img`  `<img src="divider.png" role="presentation" alt="" tabindex="0" width="300" height="4">` -> `<img src="divider.png" alt="" width="300" height="4">`
- verified: **scope-attr-valid** `td`  `<td scope="row">` -> `<td>`
- verified: **table-duplicate-name** `table`  `<table summary="Recent transactions">` -> `<table>`
- verified: **target-size** `a`  `<a href="/accounts">` -> `<a href="/accounts" style="min-width: 24px; min-height: 24px; display: inline-block">`
- verified: **target-size** `a`  `<a href="/cards">` -> `<a href="/cards" style="min-width: 24px; min-height: 24px; display: inline-block">`
- verified: **target-size** `button`  `<button class="icon" type="button" aria-label="Previous">` -> `<button class="icon" type="button" aria-label="Previous" style="min-width: 24px; min-height: 24px">`
- verified: **target-size** `button`  `<button class="icon" type="button" aria-label="Next">` -> `<button class="icon" type="button" aria-label="Next" style="min-width: 24px; min-height: 24px">`
- verified: **td-headers-attr** `table`  `<table>` -> `<table>`
- verified: **aria-prohibited-attr** `span`  `<span aria-label="Support hours">` -> `<span>`
- verified: **duplicate-id-aria** `p`  `<p id="acct-help">Use the 12-digit number on your passbook.</p>
      <input type="text" name="acct" aria-describedby="acct-help" aria-label="Reviewer typed description">
      <p id="acct-help">Joint accounts need both holders to sign.</p>` -> `<p id="acct-help">Use the 12-digit number on your passbook.</p>
      <input type="text" name="acct" aria-describedby="acct-help" aria-label="Reviewer typed description">
      <p id="acct-help-2">Joint accounts need both holders to sign.</p>`
- verified: **form-field-multiple-labels** `#pan`  `<input type="text" id="pan" name="pan">` -> `one <label for> kept`
- verified: **frame-title-unique** `iframe`  `<iframe src="offers-a.html" title="Offers" width="300" height="80">` -> `title="…"`
- verified: **video-caption** `video`  `<video src="how-to-upi.mp4" controls width="320">` -> `<track kind="captions" src="how-to-upi.en.vtt" srclang="en" label="Captions" default>`
- Manual-review queue: `region a`
  - [x] best-practice scan finds 70+ problems across 30+ rule types
  - [x] "needs review" items are found and offered as fixes too
  - [x] every approved patch verified (none rolled back)
  - [x] only page-structure items left (at most 2 region nodes)
  - [x] no needs-review items left
  - [x] original.html never modified

## PASS - B10 No landmarks notice
`examples/samples/10_no_landmarks_notice.html` - axe "needs review" for bypass blocks: reviewer picks the main content

- verified: **bypass** `html`  `<div class="page">` -> `role="main"`
  - [x] no WCAG violations, but axe asks for review of "bypass blocks"
  - [x] reviewer is asked which part is the main content
  - [x] main landmark added and verified
  - [x] original.html never modified

## PASS - B11 Investments widgets gallery
`examples/samples/11_widgets_gallery.html` - Custom ARIA widgets, moving text, image maps, skip link and duplicate landmarks

- Baseline counts: `{'area-alt': 1, 'aria-allowed-attr': 1, 'aria-command-name': 1, 'aria-dialog-name': 1, 'aria-input-field-name': 1, 'aria-meter-name': 1, 'aria-progressbar-name': 1, 'aria-tab-name': 1, 'aria-toggle-field-name': 1, 'aria-tooltip-name': 1, 'aria-treeitem-name': 1, 'blink': 1, 'frame-title': 1, 'landmark-contentinfo-is-top-level': 1, 'landmark-no-duplicate-banner': 1, 'landmark-no-duplicate-contentinfo': 1, 'landmark-unique': 2, 'region': 1, 'role-img-alt': 2, 'skip-link': 1, 'tabindex': 1}`  ->  Final counts: `{}`
- verified: **area-alt** `area`  `<area href="/equity" shape="rect" coords="0,0,50,50">` -> `alt="…"`
- verified: **aria-allowed-attr** `div`  `<div role="button" tabindex="0" aria-checked="true">` -> `<div role="button" tabindex="0">`
- verified: **aria-command-name** `div`  `<div role="button" tabindex="0">` -> `aria-label="…"`
- verified: **aria-dialog-name** `div`  `<div role="dialog">` -> `aria-label="…"`
- verified: **aria-input-field-name** `div`  `<div role="textbox" contenteditable="true">` -> `aria-label="…"`
- verified: **aria-meter-name** `div`  `<div role="meter" aria-valuenow="7" aria-valuemin="0" aria-valuemax="10">` -> `aria-label="…"`
- verified: **aria-progressbar-name** `div`  `<div role="progressbar" aria-valuenow="40" aria-valuemin="0" aria-valuemax="100">` -> `aria-label="…"`
- verified: **aria-tab-name** `div`  `<div role="tab" tabindex="0" aria-selected="true">` -> `aria-label="…"`
- verified: **aria-toggle-field-name** `div`  `<div role="switch" aria-checked="false" tabindex="0">` -> `aria-label="…"`
- verified: **aria-tooltip-name** `div`  `<div role="tooltip">` -> `aria-label="…"`
- verified: **aria-treeitem-name** `div`  `<div role="treeitem">` -> `aria-label="…"`
- verified: **blink** `blink`  `<blink>` -> `<span>`
- verified: **frame-title** `iframe`  `<iframe src="nav-chart.html" width="300" height="60">` -> `title="…"`
- verified: **landmark-contentinfo-is-top-level** `div`  `<div role="contentinfo">` -> `<div>`
- verified: **landmark-no-duplicate-banner** `header`  `<header>` -> `<section aria-label="…">`
- verified: **role-img-alt** `div`  `<div role="img">` -> `aria-label="…"`
- verified: **role-img-alt** `div`  `<div role="img" aria-braillelabel="Fund chart">` -> `aria-label="…"`
- verified: **skip-link** `.skip`  `<a href="#portfolio-start" class="skip">` -> `<a href="#main-content" class="skip">`
- verified: **tabindex** `a`  `<a href="/funds" tabindex="3">` -> `<a href="/funds" tabindex="0">`
- verified: **server-side-image-map** `img`  `<img src="map.png" alt="Branch map" ismap>` -> `<img src="map.png" alt="Branch map">`
  - [x] custom widgets without names, moving text, image maps and landmark problems detected
  - [x] every approved patch verified (none rolled back)
  - [x] no violations and no needs-review items left
  - [x] original.html never modified

## PASS - B12 Page-level settings
`examples/samples/06_accessible_login.html` - Invalid language, lang/xml:lang mismatch, zoom limits, braille-only label, hidden body (six small pages)

- Baseline counts: `{'invalid page language: html-lang-valid': 1, 'lang and xml:lang disagree: html-xml-lang-mismatch': 1, 'zoom limited to 150%: meta-viewport': 1, 'zoom limited to 300%: meta-viewport-large': 1, 'braille-only label: presentation-role-conflict': 1, 'braille-only label: review:aria-braille-equivalent': 1, 'whole page hidden from screen readers: aria-hidden-body': 1, 'whole page hidden from screen readers: landmark-one-main': 1, 'whole page hidden from screen readers: page-has-heading-one': 1}`  ->  Final counts: `{}`
- verified: **html-lang-valid** `html`  `<html lang="english">` -> `lang="…"`
- verified: **html-xml-lang-mismatch** `html`  `<html lang="en" xml:lang="fr">` -> `<html lang="en" xml:lang="en">`
- verified: **meta-viewport** `meta`  `<meta name="viewport" content="width=device-width, maximum-scale=1.5">` -> `<meta name="viewport" content="width=device-width">`
- verified: **meta-viewport-large** `meta`  `<meta name="viewport" content="width=device-width, maximum-scale=3">` -> `<meta name="viewport" content="width=device-width">`
- verified: **aria-braille-equivalent** `img`  `<img src="chart.png" alt="" aria-braillelabel="Rate chart">` -> `<img src="chart.png" alt="">`
- verified: **aria-hidden-body** `body`  `<body aria-hidden="true">` -> `<body>`
  - [x] invalid page language: detected, fixed and verified
  - [x] lang and xml:lang disagree: detected, fixed and verified
  - [x] zoom limited to 150%: detected, fixed and verified
  - [x] zoom limited to 300%: detected, fixed and verified
  - [x] braille-only label: detected, fixed and verified
  - [x] whole page hidden from screen readers: detected, fixed and verified
  - [x] every approved patch verified
  - [x] original.html never modified

## PASS - B13 Card offers: responsive and focus
`examples/samples/12_responsive_focus_gallery.html` - AccessLoop browser checks: keyboard focus, 320 px reflow, text spacing, closed details opened

- Baseline counts: `{'image-alt': 1, 'al-focus-visible': 3, 'al-text-spacing': 1, 'review:al-reflow': 1}`  ->  Final counts: `{}`
- verified: **image-alt** `img`  `<img src="fee-table.png" width="300" height="120">` -> `alt="…"`
- verified: **al-focus-visible** ``  `<head>` -> `<head>`
- verified: **al-text-spacing** ``  `<p class="teaser">` -> `<p class="teaser" style="height: auto !important; max-height: none !important; overflow: visible !important">`
- verified: **al-reflow** ``  `<div class="offer-strip">` -> `<div class="offer-strip" style="max-width: 100% !important; box-sizing: border-box; overflow-wrap: anywhere">`
  - [x] browser checks find hidden focus, clipped text, sideways scrolling and the image inside closed details
  - [x] every approved patch verified
  - [x] no violations and no needs-review items left
  - [x] original.html never modified

## PASS - B14 Account statement: duplicate main, empty header
`examples/samples/13_statement_layout.html` - Two main landmarks and a header cell that labels no data: reviewer decides, fix verified

- Baseline counts: `{'landmark-no-duplicate-main': 1, 'landmark-unique': 1}`  ->  Final counts: `{}`
- verified: **landmark-no-duplicate-main** `main`  `<main>` -> `<section aria-label="…">`
- verified: **th-has-data-cells** `table`  `<th scope="row">Closing balance as on 31 October</th>` -> `<td>…</td>`
  - [x] two main landmarks and a header cell with no data are found
  - [x] both are structural decisions: medium risk, and they need the reviewer (the agent never applies them alone)
  - [x] every approved patch verified (none rolled back)
  - [x] no violations and no needs-review items left
  - [x] the second main became a named region; the empty header became a normal cell
  - [x] original.html never modified

## PASS - B15 Agent mode on the legacy portal
`examples/samples/08_legacy_portal_gallery.html` - One run: the agent fixes what its policy allows, verifies each change and hands the rest to a person

- Baseline counts: `{'aria-roles': 1, 'aria-valid-attr': 1, 'autocomplete-valid': 1, 'button-name': 2, 'color-contrast': 1, 'document-title': 1, 'html-has-lang': 1, 'image-alt': 1, 'input-button-name': 1, 'input-image-alt': 1, 'label': 3, 'link-name': 1, 'marquee': 1, 'meta-viewport': 1, 'scrollable-region-focusable': 1, 'select-name': 1, 'summary-name': 1, 'svg-img-alt': 1, 'valid-lang': 1}`  ->  Final counts: `{'aria-roles': 1, 'aria-valid-attr': 1, 'autocomplete-valid': 1, 'button-name': 1, 'color-contrast': 1, 'document-title': 1, 'image-alt': 1, 'input-button-name': 1, 'input-image-alt': 1, 'label': 1, 'link-name': 1, 'marquee': 1, 'summary-name': 1, 'svg-img-alt': 1, 'valid-lang': 1}`
- verified: **agent** `7 fixes`  `22 violations` -> `15 violations`
- Manual-review queue: `aria-roles #fake-role`, `aria-valid-attr #typo-attr`, `autocomplete-valid #reg-email`, `button-name #icon-only`, `color-contrast .muted`, `document-title html`, `image-alt img`, `input-button-name #clear`, `input-image-alt input`, `label #wrapped`, `link-name a`, `marquee marquee`, `summary-name summary`, `svg-img-alt svg`, `valid-lang span`
  - [x] the agent ran perceive → plan → act → verify → hand over on its own
  - [x] violations fell and nothing was rolled back
  - [x] it applied only low-risk automatic fixes and typed no text
  - [x] everything else was handed to a person as a question or a held fix
  - [x] the run and its policy are in the audit log
  - [x] original.html never modified

## PASS - B6 Accessible sign-in
`examples/samples/06_accessible_login.html` - Clean control page; no false positives / edits

  - [x] zero violations on clean page
  - [x] zero proposals
  - [x] original.html never modified

## PASS - B7 Unsafe payment page
`examples/samples/07_unsafe_payment_page.html` - Script + inline handler refused at input

- Note: Refused: Inline event handlers (onclick and similar) are not supported.
  - [x] script/onclick page refused before scan
