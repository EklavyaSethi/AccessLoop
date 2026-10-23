"""Complete accessibility issue catalogue.

Two lists, both generated from real data rather than written from memory:

1. Every rule in the installed axe-core engine (data/axe_rules.json, extracted with
   ``python -m accessloop.catalog --refresh``), each classified by how AccessLoop handles it.
2. All 55 WCAG 2.2 Level A + AA success criteria, marked as partly testable by axe or
   not testable by axe at all (the "manual-only" gap), with AccessLoop's plan for each.

tests/test_catalog.py fails if axe ever has a rule that is not classified here, so no
detectable issue can be silently left out.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import re
from pathlib import Path

from .fixers import FIXERS, MODES
from .scanner import TAGS as SCAN_TAGS

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / 'data' / 'axe_rules.json'
SCANNED_PATH = ROOT / 'data' / 'axe_scanned_today.json'
AXE_PATH = ROOT / 'node_modules' / 'axe-core' / 'axe.min.js'

# --------------------------------------------------------------------------- handling classes
HANDLING = {
    'live': 'Fix available now (human-approved)',
    'auto': 'Planned: deterministic fix',
    'assisted': 'Planned: fix with reviewer input',
    'guided': 'Detected: guidance only, no edit',
    'excluded': 'Not scanned: reason given',
}

LIVE = {
    'html-has-lang': 'Adds lang="<reviewer-chosen code>" to <html>.',
    'label': 'Links an immediately adjacent visible <label> to its unique <input> with for=. Other label layouts are planned.',
    'button-name': 'Un-hides visible button text wrongly marked aria-hidden. Icon-only buttons are escalated to a human.',
}

AUTO = {
    'aria-hidden-body': 'Remove aria-hidden from <body>.',
    'blink': 'Unwrap the deprecated <blink> element, keeping its text.',
    'marquee': 'Unwrap the deprecated <marquee> element, keeping its text.',
    'html-xml-lang-mismatch': 'Make xml:lang match the lang attribute.',
    'meta-viewport': 'Remove user-scalable=no and restrictive maximum-scale so users can zoom.',
    'meta-viewport-large': 'Raise or remove maximum-scale values below 5.',
    'scope-attr-valid': 'Remove invalid scope values from table cells.',
    'scrollable-region-focusable': 'Add tabindex="0" so keyboard users can scroll the region.',
}

ASSISTED = {
    'area-alt': 'Reviewer supplies alt text for image-map areas.',
    'aria-command-name': 'Reviewer supplies an accessible name (aria-label) for the control.',
    'aria-dialog-name': 'Reviewer supplies a dialog name (aria-label / aria-labelledby).',
    'aria-input-field-name': 'Reviewer supplies an accessible name for the custom input.',
    'aria-meter-name': 'Reviewer supplies a name for the meter.',
    'aria-progressbar-name': 'Reviewer supplies a name for the progress bar.',
    'aria-tab-name': 'Reviewer supplies a name for the tab.',
    'aria-toggle-field-name': 'Reviewer supplies a name for the toggle.',
    'aria-tooltip-name': 'Reviewer supplies a name for the tooltip.',
    'aria-treeitem-name': 'Reviewer supplies a name for the tree item.',
    'autocomplete-valid': 'Suggest a valid autocomplete token from the field type/name (KYC forms); reviewer confirms.',
    'bypass': 'Insert a "Skip to main content" link and target; reviewer confirms placement.',
    'color-contrast': 'Compute the nearest colour of the same hue that reaches 4.5:1 (3:1 for large text); reviewer approves the CSS change.',
    'document-title': 'Propose a <title> from the page heading; reviewer edits and approves.',
    'frame-title': 'Reviewer supplies a title for the frame.',
    'html-lang-valid': 'Replace an invalid lang value with a reviewer-chosen code.',
    'image-alt': 'Reviewer marks the image decorative (alt="") or supplies alt text; AI may suggest wording.',
    'input-button-name': 'Reviewer supplies a value/label for the button input.',
    'input-image-alt': 'Reviewer supplies alt text for the image button.',
    'label-content-name-mismatch': 'Align the accessible name with the visible text; reviewer approves.',
    'label-title-only': 'Replace a title-only label with a real <label>; reviewer approves.',
    'link-in-text-block': 'Add an underline (or other non-colour cue) to in-text links via CSS; reviewer approves.',
    'link-name': 'Reviewer supplies link text (aria-label) or marks it for rewrite.',
    'object-alt': 'Reviewer supplies alternative text for the <object>.',
    'role-img-alt': 'Reviewer supplies alt text for the role="img" element.',
    'select-name': 'Link an adjacent <label> or add an aria-label supplied by the reviewer.',
    'skip-link': 'Fix the skip link target; reviewer confirms.',
    'summary-name': 'Reviewer supplies visible text for the <summary>.',
    'svg-img-alt': 'Reviewer supplies a name (<title>/aria-label) for the SVG image.',
    'tabindex': 'Replace positive tabindex values with 0 or remove them; reviewer checks the resulting tab order.',
    'valid-lang': 'Replace an invalid lang on a page section with a reviewer-chosen code.',
}

GUIDED = {
    'accesskeys', 'aria-allowed-attr', 'aria-allowed-role', 'aria-braille-equivalent', 'aria-conditional-attr',
    'aria-deprecated-role', 'aria-hidden-focus', 'aria-prohibited-attr', 'aria-required-attr',
    'aria-required-children', 'aria-required-parent', 'aria-roles', 'aria-text', 'aria-valid-attr-value',
    'aria-valid-attr', 'avoid-inline-spacing', 'definition-list', 'dlitem', 'duplicate-id-aria', 'empty-heading',
    'empty-table-header', 'form-field-multiple-labels',
    'frame-title-unique', 'heading-order', 'image-redundant-alt', 'landmark-banner-is-top-level',
    'landmark-contentinfo-is-top-level', 'landmark-main-is-top-level', 'landmark-no-duplicate-banner',
    'landmark-no-duplicate-contentinfo', 'landmark-no-duplicate-main', 'landmark-one-main', 'landmark-unique',
    'list', 'listitem', 'meta-refresh', 'nested-interactive', 'no-autoplay-audio', 'page-has-heading-one',
    'presentation-role-conflict', 'region', 'server-side-image-map', 'table-duplicate-name', 'target-size',
    'td-headers-attr', 'th-has-data-cells', 'video-caption',
}
GUIDED_NOTE = ('Needs a structure, design or content decision that a template cannot make safely, so '
               'AccessLoop reports it with the axe guidance link and does not edit it.')

EXCLUDED = {
    'aria-roledescription': 'Deprecated by axe.',
    'audio-caption': 'Deprecated by axe.',
    'duplicate-id': 'Deprecated by axe (WCAG 4.1.1 Parsing was removed in WCAG 2.2).',
    'duplicate-id-active': 'Deprecated by axe (WCAG 4.1.1 Parsing was removed in WCAG 2.2).',
    'landmark-complementary-is-top-level': 'Deprecated by axe.',
    'color-contrast-enhanced': 'Level AAA only; outside the WCAG AA target.',
    'identical-links-same-purpose': 'Level AAA only; outside the WCAG AA target.',
    'meta-refresh-no-exceptions': 'Level AAA only; outside the WCAG AA target.',
    'css-orientation-lock': 'Experimental in axe (off by default).',
    'focus-order-semantics': 'Experimental in axe (off by default).',
    'hidden-content': 'Experimental in axe (off by default).',
    'p-as-heading': 'Experimental in axe (off by default).',
    'table-fake-caption': 'Experimental in axe (off by default).',
    'td-has-header': 'Experimental in axe (off by default).',
    'frame-focusable-content': 'Not applicable: AccessLoop never loads frame contents (every network request is blocked '
                               'during a scan), so the frame\'s inner controls cannot be checked here.',
    'frame-tested': 'Switched off: AccessLoop never loads frame contents (every network request is blocked during a scan), '
                    'so this "was the frame tested?" check would always ask for review.',
}

# Build order: P1 = most common real-world failures (WebAIM top six) plus banking-form needs.
PRIORITY_1 = {
    'html-has-lang', 'label', 'button-name', 'image-alt', 'link-name', 'select-name', 'input-button-name',
    'document-title', 'html-lang-valid', 'valid-lang', 'color-contrast', 'autocomplete-valid', 'meta-viewport',
}

# --------------------------------------------------------------------------- WCAG 2.2 A + AA (55 criteria)
_P = {'1': 'Perceivable', '2': 'Operable', '3': 'Understandable', '4': 'Robust'}
_A = [
    ('1.1.1', 'Non-text Content'), ('1.2.1', 'Audio-only and Video-only (Prerecorded)'),
    ('1.2.2', 'Captions (Prerecorded)'), ('1.2.3', 'Audio Description or Media Alternative (Prerecorded)'),
    ('1.3.1', 'Info and Relationships'), ('1.3.2', 'Meaningful Sequence'), ('1.3.3', 'Sensory Characteristics'),
    ('1.4.1', 'Use of Color'), ('1.4.2', 'Audio Control'), ('2.1.1', 'Keyboard'), ('2.1.2', 'No Keyboard Trap'),
    ('2.1.4', 'Character Key Shortcuts'), ('2.2.1', 'Timing Adjustable'), ('2.2.2', 'Pause, Stop, Hide'),
    ('2.3.1', 'Three Flashes or Below Threshold'), ('2.4.1', 'Bypass Blocks'), ('2.4.2', 'Page Titled'),
    ('2.4.3', 'Focus Order'), ('2.4.4', 'Link Purpose (In Context)'), ('2.5.1', 'Pointer Gestures'),
    ('2.5.2', 'Pointer Cancellation'), ('2.5.3', 'Label in Name'), ('2.5.4', 'Motion Actuation'),
    ('3.1.1', 'Language of Page'), ('3.2.1', 'On Focus'), ('3.2.2', 'On Input'), ('3.2.6', 'Consistent Help'),
    ('3.3.1', 'Error Identification'), ('3.3.2', 'Labels or Instructions'), ('3.3.7', 'Redundant Entry'),
    ('4.1.2', 'Name, Role, Value'),
]
_AA = [
    ('1.2.4', 'Captions (Live)'), ('1.2.5', 'Audio Description (Prerecorded)'), ('1.3.4', 'Orientation'),
    ('1.3.5', 'Identify Input Purpose'), ('1.4.3', 'Contrast (Minimum)'), ('1.4.4', 'Resize Text'),
    ('1.4.5', 'Images of Text'), ('1.4.10', 'Reflow'), ('1.4.11', 'Non-text Contrast'), ('1.4.12', 'Text Spacing'),
    ('1.4.13', 'Content on Hover or Focus'), ('2.4.5', 'Multiple Ways'), ('2.4.6', 'Headings and Labels'),
    ('2.4.7', 'Focus Visible'), ('2.4.11', 'Focus Not Obscured (Minimum)'), ('2.5.7', 'Dragging Movements'),
    ('2.5.8', 'Target Size (Minimum)'), ('3.1.2', 'Language of Parts'), ('3.2.3', 'Consistent Navigation'),
    ('3.2.4', 'Consistent Identification'), ('3.3.3', 'Error Suggestion'),
    ('3.3.4', 'Error Prevention (Legal, Financial, Data)'), ('3.3.8', 'Accessible Authentication (Minimum)'),
    ('4.1.3', 'Status Messages'),
]
CRITERIA = ([(n, t, 'A') for n, t in _A] + [(n, t, 'AA') for n, t in _AA])

# What AccessLoop could add for criteria axe cannot test. kind: 'browser' (our own Playwright check),
# 'site' (needs several pages), 'manual' (human judgement). All are PLANNED, none is built yet.
SUPPLEMENT = {
    '1.4.10': ('browser', 'Render at 320 px width and flag horizontal scrolling.'),
    '2.1.2': ('browser', 'Tab through the page and flag any element focus cannot leave.'),
    '2.4.3': ('browser', 'Record the Tab order and show it for human review.'),
    '2.4.7': ('browser', 'Tab through the page and flag controls with no visible focus change.'),
    '2.4.11': ('browser', 'While tabbing, flag focused controls hidden behind sticky headers or footers.'),
    '1.4.11': ('browser', 'Measure border and icon contrast of form controls against the 3:1 minimum.'),
    '2.4.5': ('site', 'In whole-site mode, check there is more than one way to find pages (navigation plus search or sitemap).'),
    '3.2.3': ('site', 'In whole-site mode, compare navigation order across pages.'),
    '3.2.4': ('site', 'In whole-site mode, compare labels of repeated components across pages.'),
    '3.2.6': ('site', 'In whole-site mode, check help links appear in the same place on every page.'),
}
BFSI_NOTE = {
    '1.3.5': 'KYC and sign-up forms: browsers and assistive tech can auto-fill name, address, phone and email.',
    '2.2.1': 'Banking sessions time out; users need warning and a way to extend.',
    '3.3.1': 'Form errors on KYC, payments and claims must be identified in text.',
    '3.3.2': 'Every field on an application form needs a visible label or instruction.',
    '3.3.3': 'Failed entries (account numbers, IFSC, PAN) need a suggested correction.',
    '3.3.4': 'Financial and legal submissions must be reversible, checked or confirmed.',
    '3.3.7': 'Do not make users re-enter information already given in the same process.',
    '3.3.8': 'Login and OTP steps must not rely on memorising or transcribing codes with no alternative.',
    '4.1.3': 'Transaction results and balance updates must be announced to screen readers.',
}


# --------------------------------------------------------------------------- helpers
def _criteria_from_tags(tags: list[str]) -> list[str]:
    out = []
    for tag in tags:
        m = re.fullmatch(r'wcag(\d)(\d)(\d+)', tag)
        if m:
            out.append(f'{m.group(1)}.{m.group(2)}.{m.group(3)}')
    return out


def _level(tags: list[str]) -> str:
    if any(t in tags for t in ('wcag2a', 'wcag21a', 'wcag22a')):
        return 'A'
    if any(t in tags for t in ('wcag2aa', 'wcag21aa', 'wcag22aa')):
        return 'AA'
    if 'wcag2aaa' in tags:
        return 'AAA'
    if 'wcag2a-obsolete' in tags:
        return 'obsolete'
    return 'best-practice'


def _category(tags: list[str]) -> str:
    for tag in tags:
        if tag.startswith('cat.'):
            return tag[4:]
    return ''


_MODE_NOTE = {
    'auto': 'Fixed with your approval. ',
    'input': 'Fixed with the text you type; AccessLoop never guesses it. ',
    'mixed': 'Fixed automatically when the page makes the answer clear, otherwise you type it. ',
}
# Every rule that has a real fixer in accessloop/fixers.py is "live"; it leaves the planned lists automatically.
OWN_CHECKS = sorted(r for r in FIXERS if r.startswith('al-'))   # AccessLoop's own browser checks, not axe rules
for _rule in sorted(r for r in FIXERS if not r.startswith('al-')):
    _detail = LIVE.get(_rule) or AUTO.pop(_rule, None) or ASSISTED.pop(_rule, None) or ''
    AUTO.pop(_rule, None)
    ASSISTED.pop(_rule, None)
    GUIDED.discard(_rule)
    LIVE[_rule] = _MODE_NOTE[MODES[_rule]] + _detail


def handling_of(rule_id: str) -> str | None:
    for name, group in (('live', LIVE), ('auto', AUTO), ('assisted', ASSISTED), ('guided', GUIDED), ('excluded', EXCLUDED)):
        if rule_id in group:
            return name
    return None


def unclassified(rule_ids) -> list[str]:
    return sorted(i for i in rule_ids if handling_of(i) is None)


def overlapping() -> list[str]:
    groups = [set(LIVE), set(AUTO), set(ASSISTED), GUIDED, set(EXCLUDED)]
    seen, dup = set(), set()
    for group in groups:
        dup |= seen & group
        seen |= group
    return sorted(dup)


def load_rules(path: Path = RULES_PATH) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def load_scanned(path: Path = SCANNED_PATH) -> set[str]:
    return set(json.loads(path.read_text(encoding='utf-8')))


def build(rules_doc: dict | None = None, scanned: set[str] | None = None) -> dict:
    rules_doc = rules_doc or load_rules()
    scanned = scanned if scanned is not None else load_scanned()
    rows = []
    for rule in sorted(rules_doc['rules'], key=lambda r: r['ruleId']):
        rid, tags = rule['ruleId'], rule['tags']
        h = handling_of(rid)
        if h == 'live':
            note = LIVE[rid]
        elif h == 'auto':
            note = AUTO[rid]
        elif h == 'assisted':
            note = ASSISTED[rid]
        elif h == 'excluded':
            note = EXCLUDED[rid]
        elif h == 'guided':
            note = GUIDED_NOTE
        else:
            note = 'UNCLASSIFIED: add this rule to accessloop/catalog.py'
        priority = ''
        if h in ('live', 'auto', 'assisted'):
            priority = 'P1' if rid in PRIORITY_1 else 'P2'
        rows.append({
            'rule_id': rid, 'title': rule['help'], 'description': rule['description'],
            'wcag': _criteria_from_tags(tags), 'level': _level(tags), 'category': _category(tags),
            'scanned_today': rid in scanned, 'handling': h or 'unclassified', 'priority': priority,
            'note': note, 'help_url': rule['helpUrl'],
        })
    by_rule: dict[str, list[str]] = {}
    for row in rows:
        for c in row['wcag']:
            by_rule.setdefault(c, []).append(row['rule_id'])
    criteria = []
    for num, name, level in CRITERIA:
        axe_rules = by_rule.get(num, [])
        sup = SUPPLEMENT.get(num)
        criteria.append({
            'criterion': num, 'name': name, 'level': level, 'principle': _P[num[0]],
            'axe_rules': axe_rules, 'axe_testable': bool(axe_rules),
            'next_step': {'kind': sup[0], 'text': sup[1]} if sup else
                         ({'kind': 'axe', 'text': 'Partly testable by axe; manual checks still needed.'} if axe_rules else
                          {'kind': 'manual', 'text': 'Needs a human check; AccessLoop lists it in the manual checklist.'}),
            'bfsi': BFSI_NOTE.get(num, ''),
        })
    counts = {k: sum(1 for r in rows if r['handling'] == k) for k in HANDLING}
    best_practice_skipped = [r['rule_id'] for r in rows
                             if r['level'] == 'best-practice' and not r['scanned_today'] and r['handling'] != 'excluded']
    return {
        'axe_version': rules_doc['version'], 'rules': rows, 'criteria': criteria,
        'summary': {
            'total_rules': len(rows), 'by_handling': counts,
            'scanned_today': sum(1 for r in rows if r['scanned_today']),
            'not_scanned_today': sum(1 for r in rows if not r['scanned_today']),
            'best_practice_not_scanned': best_practice_skipped,
            'best_practice_optional': len(best_practice_skipped),
            'criteria_total': len(criteria),
            'criteria_axe_testable': sum(1 for c in criteria if c['axe_testable']),
            'criteria_manual_only': sum(1 for c in criteria if not c['axe_testable']),
            'criteria_with_planned_check': sum(1 for c in criteria if c['next_step']['kind'] in ('browser', 'site')),
        },
    }


# --------------------------------------------------------------------------- outputs
def to_csv(catalog: dict) -> str:
    buf = io.StringIO()
    fields = ['rule_id', 'title', 'wcag', 'level', 'category', 'scanned_today', 'handling', 'priority', 'note', 'help_url']
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in catalog['rules']:
        writer.writerow({**row, 'wcag': ' '.join(row['wcag'])})
    return buf.getvalue()


def _esc(text: str) -> str:
    return str(text).replace('|', '\\|').replace('<', '&lt;').replace('>', '&gt;')


def to_markdown(catalog: dict) -> str:
    s = catalog['summary']
    h = s['by_handling']
    lines = [
        '# AccessLoop issue catalogue', '',
        f'Generated from the real axe-core engine (version {catalog["axe_version"]}) and the 55 WCAG 2.2 Level A and AA '
        'success criteria. Regenerate with `python -m accessloop.catalog`.', '',
        '> **Scope note.** No list can contain every possible accessibility barrier, because usability for real people is not '
        'a finite checklist. This catalogue is complete against the two standards that matter for compliance work: every rule '
        'the axe engine can detect, and every WCAG 2.2 A/AA criterion. Where a tool cannot test a criterion, it is listed as '
        'manual-only rather than left out.', '',
        '## 1. Summary', '',
        f'- axe rules in the engine: **{s["total_rules"]}**. Run by AccessLoop today: **{s["scanned_today"]}**. '
        f'Not run: **{s["not_scanned_today"]}**.',
        f'- Handling today: **{h["live"]}** with a live human-approved fix, **{h["auto"]}** planned deterministic fixes, '
        f'**{h["assisted"]}** planned reviewer-assisted fixes, **{h["guided"]}** guidance-only, **{h["excluded"]}** excluded '
        '(deprecated, experimental or AAA).',
        f'- WCAG 2.2 A + AA criteria: **{s["criteria_total"]}**. At least partly testable by axe: '
        f'**{s["criteria_axe_testable"]}**. Not testable by axe at all: **{s["criteria_manual_only"]}**, of which '
        f'**{s["criteria_with_planned_check"]}** could get an AccessLoop-built browser or site check.',
        f'- **Best-practice checks (optional):** {len(s["best_practice_not_scanned"])} more rules (heading order, landmarks, '
        'skip link, empty headings and more) run when "Include best-practice checks" is turned on. Auditors usually report '
        'these; they are off by default because they are not WCAG failures.',
        '- axe "needs review" results (where the engine cannot decide) are listed too, and many of them can be fixed and '
        're-verified the same way.', '',
        '## 2. How AccessLoop handles each rule', '',
        '| Handling | Meaning |', '|---|---|',
    ]
    for key, label in HANDLING.items():
        lines.append(f'| `{key}` | {label} |')
    lines += ['', 'Priority: **P1** = most common real-world failures (WebAIM top six) and banking-form needs; **P2** = next.', '']
    order = ['live', 'auto', 'assisted', 'guided', 'excluded']
    titles = {'live': '3. Live fixes (human-approved)', 'auto': '4. Planned: deterministic fixes',
              'assisted': '5. Planned: reviewer-assisted fixes', 'guided': '6. Guidance only',
              'excluded': '7. Excluded from scanning'}
    for key in order:
        rows = [r for r in catalog['rules'] if r['handling'] == key]
        lines += [f'## {titles[key]} ({len(rows)})', '']
        if key == 'guided':
            lines += [GUIDED_NOTE, '', '| Rule | WCAG | Level | Scanned today |', '|---|---|---|---|']
            for r in rows:
                lines.append(f'| `{r["rule_id"]}` | {_esc(", ".join(r["wcag"]) or "-")} | {r["level"]} | {"yes" if r["scanned_today"] else "no"} |')
        elif key == 'excluded':
            lines += ['| Rule | Reason |', '|---|---|']
            for r in rows:
                lines.append(f'| `{r["rule_id"]}` | {_esc(r["note"])} |')
        else:
            lines += ['| Rule | WCAG | Level | Priority | Scanned today | What AccessLoop does |', '|---|---|---|---|---|---|']
            for r in rows:
                lines.append(f'| `{r["rule_id"]}` | {_esc(", ".join(r["wcag"]) or "-")} | {r["level"]} | {r["priority"]} | '
                             f'{"yes" if r["scanned_today"] else "no"} | {_esc(r["note"])} |')
        lines.append('')
    lines += ['## 8. All 55 WCAG 2.2 A + AA criteria', '',
              '| Criterion | Name | Level | axe rules | Next step | Why it matters for BFSI |', '|---|---|---|---|---|---|']
    for c in catalog['criteria']:
        axe = ', '.join(f'`{r}`' for r in c['axe_rules']) or '**none (manual-only)**'
        lines.append(f'| {c["criterion"]} | {_esc(c["name"])} | {c["level"]} | {axe} | {_esc(c["next_step"]["text"])} | {_esc(c["bfsi"])} |')
    from .scanner import CUSTOM_RULES
    lines += ['', "## 9. AccessLoop's own browser checks (beyond axe)", '',
              'Run when "AccessLoop browser checks" is on. They test what axe cannot see in a single static render.', '',
              '| Check | WCAG | Fix |', '|---|---|---|']
    for rid, info in CUSTOM_RULES.items():
        lines.append(f'| `{rid}`: {_esc(info["title"])} | {", ".join(info["wcag"])} | '
                     f'{"automatic, human-approved" if rid in FIXERS else "guidance (needs a design decision)"} |')
    lines += ['', '## 10. Best-practice rules (run when best-practice checks are on)', '']
    lines += [', '.join(f'`{r}`' for r in s['best_practice_not_scanned']) or 'None.']
    lines += ['', '---', 'Automated tools cannot certify WCAG conformance; keyboard, screen-reader and human usability testing '
              'remain necessary.', '']
    return '\n'.join(lines)


def refresh_from_axe() -> None:
    """Re-extract the rule list and the set of rules the current scan configuration actually runs."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content('<html lang="en"><head><title>t</title></head><body><main><h1>x</h1></main></body></html>')
            page.add_script_tag(path=str(AXE_PATH))
            doc = page.evaluate('() => ({version: axe.version, rules: axe.getRules()})')
            ran = page.evaluate('''async (tags) => {
                const r = await axe.run(document, {runOnly: {type: 'tag', values: tags},
                    resultTypes: ['violations', 'incomplete', 'passes', 'inapplicable']});
                return [].concat(r.violations, r.incomplete, r.passes, r.inapplicable).map(x => x.id);
            }''', list(SCAN_TAGS))
        finally:
            browser.close()
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULES_PATH.write_text(json.dumps(doc, indent=1), encoding='utf-8')
    SCANNED_PATH.write_text(json.dumps(sorted(set(ran)), indent=1), encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate the AccessLoop issue catalogue.')
    parser.add_argument('--refresh', action='store_true', help='re-extract rules from the installed axe-core first')
    args = parser.parse_args()
    if args.refresh:
        refresh_from_axe()
    catalog = build()
    bad = unclassified(r['rule_id'] for r in catalog['rules'])
    if bad:
        print('UNCLASSIFIED axe rules, add them to accessloop/catalog.py:', ', '.join(bad))
        return 1
    (ROOT / 'docs').mkdir(exist_ok=True)
    (ROOT / 'docs' / 'ISSUE_CATALOG.md').write_text(to_markdown(catalog), encoding='utf-8')
    (ROOT / 'data' / 'issue_catalog.csv').write_text(to_csv(catalog), encoding='utf-8')
    (ROOT / 'data' / 'issue_catalog.json').write_text(json.dumps(catalog, indent=1), encoding='utf-8')
    print(json.dumps(catalog['summary'], indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
