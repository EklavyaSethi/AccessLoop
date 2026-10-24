"""Real-browser acceptance suite over examples/ + examples/samples/.

Runs every sample through the actual Workflow (Chromium + axe-core), checks the
expected agent behaviour (fix / abstain / refuse), and writes a report.

    python -m accessloop.sample_suite [--out sample_results]
"""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from .planner import sha256
from .workflow import Workflow, WorkflowError

ROOT = Path(__file__).resolve().parent.parent
SUPPORTED = ('html-has-lang', 'label', 'button-name')


@dataclass
class CaseResult:
    name: str
    file: str
    purpose: str
    passed: bool = True
    checks: list[tuple[str, bool]] = field(default_factory=list)
    baseline: dict = field(default_factory=dict)
    final: dict = field(default_factory=dict)
    applied: list[dict] = field(default_factory=list)
    manual_queue: list[str] = field(default_factory=list)
    note: str = ''

    def check(self, label: str, ok: bool) -> None:
        self.checks.append((label, bool(ok)))
        self.passed = self.passed and bool(ok)


def typed_values(p, overrides: dict | None = None) -> dict | None:
    """Stand-in for the human reviewer: supplies text for input-mode proposals. Auto proposals need none."""
    if not p.needs_input:
        return None
    over = (overrides or {}).get(p.rule_id, {})
    values: dict = {}
    for fld in p.fields:
        name = fld['name']
        if name in over:
            values[name] = over[name]
        elif fld['kind'] == 'select':
            values[name] = fld['options'][0][0]
        elif fld['kind'] == 'checkbox':
            values[name] = False
        else:
            values[name] = 'Reviewer typed description' + ('' if name in ('text', 'alt', 'title') else f' {name}')
    return values


def _approve_all(engine: Workflow, result: CaseResult, language: str = 'en', limit: int = 40,
                 overrides: dict | None = None) -> None:
    """Approve every proposal once. A proposal that is rolled back is recorded and not retried."""
    tried: set[str] = set()
    for _ in range(limit):
        todo = [p for p in engine.proposals if (p.rule_id, p.selector, p.before) not in tried]
        if not todo:
            return
        p = todo[0]
        tried.add((p.rule_id, p.selector, p.before))   # ids change after every write; the element does not
        out = engine.apply(p.proposal_id, approved=True, language=language, values=typed_values(p, overrides))
        result.applied.append({'rule': p.rule_id, 'selector': p.selector, 'status': out.status,
                               'before': p.before, 'after': p.after, 'detail': out.detail})
    result.check('loop terminates within limit', False)


def _finish(engine: Workflow, result: CaseResult, out_dir: Path | None, stem: str) -> None:
    result.final = dict(engine.current_scan.counts())
    result.manual_queue = [f'{f.rule_id} {f.selector}' for f in engine.current_scan.findings]
    if out_dir:
        (out_dir / f'{stem}.repaired.html').write_text(engine.current_html, encoding='utf-8')
        (out_dir / f'{stem}.evidence.json').write_text(engine.report_json(), encoding='utf-8')


def run_case(name: str, file: str, purpose: str, body: Callable[[Workflow, str, CaseResult], None],
             out_dir: Path | None) -> CaseResult:
    path = ROOT / file
    source = path.read_text(encoding='utf-8')
    result = CaseResult(name, file, purpose)
    with TemporaryDirectory() as tmp:
        engine = Workflow(Path(tmp))
        try:
            body(engine, source, result)
            if engine.loaded and engine.current_scan is not None:
                result.check('original.html never modified',
                             sha256((Path(tmp) / 'original.html').read_text(encoding='utf-8')) == sha256(source))
                _finish(engine, result, out_dir, path.stem)
        except Exception as error:  # an unexpected crash is a failed case, not a suite crash
            result.check(f'no unexpected exception ({type(error).__name__}: {error})', False)
    return result


# ---------- case bodies ----------

def seeded_demo(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('3 seeded rules detected', set(SUPPORTED) <= r.baseline.keys())
    _approve_all(engine, r)
    r.check('every applied patch verified', r.applied and all(a['status'] == 'verified' for a in r.applied))
    r.check('seeded rules cleared', not any(engine.current_scan.counts()[k] for k in SUPPORTED))


def kyc_onboarding(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('html-has-lang=1, label=4, button-name=1 detected',
            r.baseline.get('html-has-lang') == 1 and r.baseline.get('label') == 4 and r.baseline.get('button-name') == 1)
    r.check('6 proposals generated', len(engine.proposals) == 6)
    # Human rejects first: must not write.
    h = sha256(engine.current_html)
    engine.reject(engine.proposals[0].proposal_id)
    r.check('reject leaves working file byte-identical', sha256(engine.current_html) == h)
    # approved=False is treated as rejection.
    engine.apply(engine.proposals[0].proposal_id, approved=False)
    r.check('approved=False leaves working file byte-identical', sha256(engine.current_html) == h)
    # Stale proposal must be blocked after another edit lands.
    stale = engine.proposals[-1]
    _approve_all(engine, r)
    try:
        engine.apply(stale.proposal_id, approved=True)
        r.check('stale proposal blocked', False)
    except WorkflowError:
        r.check('stale proposal blocked', True)
    r.check('6 patches applied, all verified', len(r.applied) == 6 and all(a['status'] == 'verified' for a in r.applied))
    r.check('total violations reach 0', len(engine.current_scan.findings) == 0)


def kyc_bad_language(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan(language='english').counts())
    r.check('invalid language code -> no html-has-lang proposal',
            not any(p.rule_id == 'html-has-lang' for p in engine.proposals))
    r.check('other proposals still offered', len(engine.proposals) == 5)
    r.note = 'Reviewer language "english" is not a BCP-47 code; agent abstains for that rule only.'


def sip_signup(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('language, labels, image, link and select problems detected',
            r.baseline.get('html-has-lang') == 1 and r.baseline.get('label') == 2
            and {'image-alt', 'link-name', 'select-name'} <= r.baseline.keys())
    inputs = sorted(p.rule_id for p in engine.proposals if p.needs_input)
    r.check('alt text, link name and select name ask the reviewer (never guessed)',
            inputs == ['image-alt', 'link-name', 'select-name'])
    # Approving an input fix without typing anything must be refused and change nothing.
    h = sha256(engine.current_html)
    first_input = next(p for p in engine.proposals if p.needs_input)
    try:
        engine.apply(first_input.proposal_id, approved=True)
        r.check('input fix without typed text refused', False)
    except WorkflowError:
        r.check('input fix without typed text refused', sha256(engine.current_html) == h)
    _approve_all(engine, r)
    r.check('6 patches, all verified', len(r.applied) == 6 and all(a['status'] == 'verified' for a in r.applied))
    r.check('total violations reach 0', len(engine.current_scan.findings) == 0)


def loan_emi(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('3 labels and 1 button name detected', r.baseline.get('label') == 3 and r.baseline.get('button-name') == 1)
    btn = [p for p in engine.proposals if p.rule_id == 'button-name']
    r.check('icon-only reset button asks the reviewer instead of guessing', len(btn) == 1 and btn[0].needs_input)
    _approve_all(engine, r, overrides={'button-name': {'text': 'Reset calculator'}})
    r.check('all verified, violations reach 0',
            all(a['status'] == 'verified' for a in r.applied) and not engine.current_scan.findings)


def insurance_claim(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('language, 3 labels, button name detected',
            r.baseline.get('html-has-lang') == 1 and r.baseline.get('label') == 3 and r.baseline.get('button-name') == 1)
    r.check('already-labelled textarea is not touched', len(engine.proposals) == 5)
    _approve_all(engine, r)
    r.check('5 patches applied, all verified', len(r.applied) == 5 and all(a['status'] == 'verified' for a in r.applied))
    r.check('total violations reach 0', len(engine.current_scan.findings) == 0)


def tricky(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('label, button-name and link-name findings detected',
            r.baseline.get('label') == 4 and r.baseline.get('button-name') == 3 and r.baseline.get('link-name') == 1)
    r.check('ambiguous patterns ask the reviewer; clear ones are auto',
            sum(p.needs_input for p in engine.proposals) >= 4 and sum(not p.needs_input for p in engine.proposals) >= 3)
    # A careless reviewer types a link name that contradicts the words people can see on screen.
    link = next(p for p in engine.proposals if p.rule_id == 'link-name')
    h = sha256(engine.current_html)
    out = engine.apply(link.proposal_id, approved=True, values={'text': 'Download'})
    r.applied.append({'rule': link.rule_id, 'selector': link.selector, 'status': out.status, 'before': link.before,
                      'after': 'aria-label="Download"', 'detail': out.detail})
    r.check('typed name that contradicts the visible text is rolled back by the re-scan, file unchanged',
            out.status == 'rolled_back' and 'label-content-name-mismatch' in out.detail and sha256(engine.current_html) == h)
    link = next(p for p in engine.proposals if p.rule_id == 'link-name')
    out = engine.apply(link.proposal_id, approved=True, values={'text': 'Statements'})
    r.check('typed name that matches the visible text is verified', out.status == 'verified')
    _approve_all(engine, r)
    r.check('every remaining fix verified', all(a['status'] == 'verified' for a in r.applied[1:]))
    r.check('total violations reach 0', len(engine.current_scan.findings) == 0)


def gallery(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('legacy portal has 20+ defects across 15+ rule types',
            sum(r.baseline.values()) >= 20 and len(r.baseline) >= 15)
    r.check('every finding gets a proposal', len(engine.proposals) == sum(r.baseline.values()))
    _approve_all(engine, r, limit=60)
    r.check('every patch verified (none rolled back)', all(a['status'] == 'verified' for a in r.applied))
    r.check('total violations reach 0', len(engine.current_scan.findings) == 0)


REVIEWER_CHOICES = {'aria-hidden-focus': {'choice': 'unfocus'}, 'aria-required-attr': {'aria-checked': 'false'},
                    'video-caption': {'how': 'write', 'src': 'media/how-to-upi.en.vtt', 'cues': '0:00 Open your UPI app\n0:04 Tap Send money'}, 'meta-refresh': {'choice': 'remove'}}


def structure_gallery(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan(best_practice=True).counts())
    reviews = engine.current_scan.review_counts()
    r.check('best-practice scan finds 70+ problems across 30+ rule types',
            sum(r.baseline.values()) >= 70 and len(r.baseline) >= 30)
    r.check('"needs review" items are found and offered as fixes too',
            sum(reviews.values()) >= 5 and any(p.rule_id in reviews for p in engine.proposals))
    _approve_all(engine, r, limit=120, overrides=REVIEWER_CHOICES)
    r.check('every approved patch verified (none rolled back)',
            r.applied and all(a['status'] == 'verified' for a in r.applied))
    left = engine.current_scan.counts()
    r.check('only page-structure items left (at most 2 region nodes)', set(left) <= {'region'} and left['region'] <= 2)
    r.check('no needs-review items left', not engine.current_scan.reviews)


def no_landmarks(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('no WCAG violations, but axe asks for review of "bypass blocks"',
            not r.baseline and engine.current_scan.review_counts()['bypass'] == 1)
    p = next(p for p in engine.proposals if p.rule_id == 'bypass')
    r.check('reviewer is asked which part is the main content', p.needs_input and p.fields[0]['kind'] == 'select')
    notice = next(v for v, label in p.fields[0]['options'] if 'notice' in label)
    out = engine.apply(p.proposal_id, approved=True, values={'main': notice})
    r.applied.append({'rule': p.rule_id, 'selector': p.selector, 'status': out.status, 'before': p.before,
                      'after': 'role="main"', 'detail': out.detail})
    r.check('main landmark added and verified', out.status == 'verified' and 'role="main"' in engine.current_html)


def widgets_gallery(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan(best_practice=True).counts())
    r.check('custom widgets without names, moving text, image maps and landmark problems detected',
            len(r.baseline) >= 18)
    _approve_all(engine, r, limit=60, overrides={'landmark-no-duplicate-banner': {'name': 'Market status'}})
    r.check('every approved patch verified (none rolled back)',
            r.applied and all(a['status'] == 'verified' for a in r.applied))
    r.check('no violations and no needs-review items left',
            not engine.current_scan.findings and not engine.current_scan.reviews)


def statement_layout(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan(best_practice=True).counts())
    reviews = engine.current_scan.review_counts()
    r.check('two main landmarks and a header cell with no data are found',
            r.baseline.get('landmark-no-duplicate-main') and reviews.get('th-has-data-cells'))
    held = [p for p in engine.proposals if p.rule_id in ('landmark-no-duplicate-main', 'th-has-data-cells')]
    r.check('both are structural decisions: medium risk, and they need the reviewer (the agent never applies them alone)',
            len(held) == 2 and all(p.needs_input and p.risk == 'medium' for p in held))
    _approve_all(engine, r, limit=20, overrides={'landmark-no-duplicate-main': {'name': 'Offers for you'}})
    r.check('every approved patch verified (none rolled back)',
            r.applied and all(a['status'] == 'verified' for a in r.applied))
    r.check('no violations and no needs-review items left', not engine.current_scan.findings and not engine.current_scan.reviews)
    r.check('the second main became a named region; the empty header became a normal cell',
            'aria-label="Offers for you"' in engine.current_html and '<td scope' not in engine.current_html
            and '<td>Closing balance' in engine.current_html.replace('<td >', '<td>'))


def agent_mode(engine, source, r):
    from . import agent
    engine.load(source)
    r.baseline = dict(engine.scan(best_practice=True).counts())
    steps = []
    run = agent.run(engine, agent.Policy(), reviewer='Agent (policy approved by suite)', on_step=lambda s, _: steps.append(s.phase))
    r.applied += [{'rule': 'agent', 'selector': f'{run.applied} fixes', 'status': 'verified' if run.after < run.before else 'unchanged',
                   'before': f'{run.before} violations', 'after': f'{run.after} violations', 'detail': run.policy.describe()}]
    r.check('the agent ran perceive → plan → act → verify → hand over on its own', steps[0] == 'perceive' and 'commit' in steps
            and steps[-1] == 'stop')
    r.check('violations fell and nothing was rolled back', run.after < run.before and run.rolled_back == 0)
    r.check('it applied only low-risk automatic fixes and typed no text',
            all(p.needs_input or p.risk != 'low' for p in engine.proposals))
    r.check('everything else was handed to a person as a question or a held fix', run.questions and run.held)
    r.check('the run and its policy are in the audit log',
            any(e['event'] == 'agent_started' for e in engine.events) and engine.events[-1]['event'] == 'agent_finished')


PAGE_SETTINGS = [   # (problem, page) - small whole-page problems, each fixed on its own page
    ('invalid page language', '<!doctype html><html lang="english"><head><title>Rates</title></head><body><main><h1>Rates</h1></main></body></html>'),
    ('lang and xml:lang disagree', '<!doctype html><html lang="en" xml:lang="fr"><head><title>Rates</title></head><body><main><h1>Rates</h1></main></body></html>'),
    ('zoom limited to 150%', '<!doctype html><html lang="en"><head><title>Rates</title><meta name="viewport" content="width=device-width, maximum-scale=1.5"></head><body><main><h1>Rates</h1></main></body></html>'),
    ('zoom limited to 300%', '<!doctype html><html lang="en"><head><title>Rates</title><meta name="viewport" content="width=device-width, maximum-scale=3"></head><body><main><h1>Rates</h1></main></body></html>'),
    ('braille-only label', '<!doctype html><html lang="en"><head><title>Rates</title></head><body><main><h1>Rates</h1><img src="chart.png" alt="" aria-braillelabel="Rate chart"></main></body></html>'),
    ('whole page hidden from screen readers', '<!doctype html><html lang="en"><head><title>Rates</title></head><body aria-hidden="true"><main><h1>Rates</h1></main></body></html>'),
]


def page_settings(engine, source, r):
    for problem, page in PAGE_SETTINGS:
        engine.load(page)
        before = engine.scan(best_practice=True)
        found = dict(before.counts())
        found.update({f'review:{k}': v for k, v in before.review_counts().items()})
        r.baseline.update({f'{problem}: {k}': v for k, v in found.items()})
        _approve_all(engine, r, overrides={'html-lang-valid': {'lang': 'en'}})
        found.update({f'review:{k}': v for k, v in before.review_counts().items()})
        r.check(f'{problem}: detected, fixed and verified',
                bool(found) and not engine.current_scan.findings and not engine.current_scan.reviews)
    r.check('every approved patch verified', r.applied and all(a['status'] == 'verified' for a in r.applied))
    engine.load(source)          # finish on the case's own file so the shared end-of-case checks apply
    engine.scan()


def responsive_focus(engine, source, r):
    engine.load(source)
    sc = engine.scan(best_practice=True, extended=True)
    r.baseline = dict(sc.counts())
    r.baseline.update({f'review:{k}': v for k, v in sc.review_counts().items()})
    r.check('browser checks find hidden focus, clipped text, sideways scrolling and the image inside closed details',
            sc.counts()['al-focus-visible'] >= 3 and sc.counts()['al-text-spacing'] >= 1
            and sc.review_counts()['al-reflow'] >= 1 and sc.counts()['image-alt'] == 1)
    _approve_all(engine, r)
    r.check('every approved patch verified', r.applied and all(a['status'] == 'verified' for a in r.applied))
    r.check('no violations and no needs-review items left', not engine.current_scan.findings and not engine.current_scan.reviews)


def accessible(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('zero violations on clean page', not r.baseline)
    r.check('zero proposals', engine.proposals == ())


def unsafe(engine, source, r):
    try:
        engine.load(source)
        r.check('script/onclick page refused before scan', False)
    except WorkflowError as error:
        r.check('script/onclick page refused before scan', True)
        r.note = f'Refused: {error}'


def ambiguous_icon(engine, source, r):
    engine.load(source)
    r.baseline = dict(engine.scan().counts())
    r.check('button-name detected', r.baseline.get('button-name') == 1)
    r.check('no invented label: one input proposal, nothing written yet',
            len(engine.proposals) == 1 and engine.proposals[0].needs_input and engine.current_html == source)


CASES = [
    ('Starter demo (regression)', 'examples/student_registration.html', 'Original starter page: 3 seeded rules fixed end-to-end', seeded_demo),
    ('Starter ambiguous icon (regression)', 'examples/ambiguous_icon_button.html', 'Icon-only button asks the reviewer, never guessed', ambiguous_icon),
    ('B1 KYC onboarding', 'examples/samples/01_kyc_onboarding.html', 'Many instances + reject / no-approval / stale guards on a KYC form', kyc_onboarding),
    ('B1b Invalid language', 'examples/samples/01_kyc_onboarding.html', 'Bad reviewer language input', kyc_bad_language),
    ('B2 SIP sign-up', 'examples/samples/02_sip_signup.html', 'Mixed: auto fixes plus three fixes that need reviewer-typed text', sip_signup),
    ('B3 Loan EMI calculator', 'examples/samples/03_loan_emi_calculator.html', 'Labels auto-fixed; icon-only reset button asks the reviewer', loan_emi),
    ('B4 Insurance claim', 'examples/samples/04_insurance_claim.html', 'Claim form fully repaired and verified', insurance_claim),
    ('B5 Payment edge cases', 'examples/samples/05_banking_edge_cases.html', 'Near-miss patterns on a payment form: ask, never guess; contradicting typed text is rolled back', tricky),
    ('B8 Legacy portal gallery', 'examples/samples/08_legacy_portal_gallery.html', '22 defects across 20 rule types, all fixed and verified', gallery),
    ('B9 Net-banking structure gallery', 'examples/samples/09_netbanking_structure_gallery.html',
     'Best-practice + needs-review: 80+ problems across 35+ rule types, all fixed and verified', structure_gallery),
    ('B10 No landmarks notice', 'examples/samples/10_no_landmarks_notice.html',
     'axe "needs review" for bypass blocks: reviewer picks the main content', no_landmarks),
    ('B11 Investments widgets gallery', 'examples/samples/11_widgets_gallery.html',
     'Custom ARIA widgets, moving text, image maps, skip link and duplicate landmarks', widgets_gallery),
    ('B12 Page-level settings', 'examples/samples/06_accessible_login.html',
     'Invalid language, lang/xml:lang mismatch, zoom limits, braille-only label, hidden body (six small pages)', page_settings),
    ('B13 Card offers: responsive and focus', 'examples/samples/12_responsive_focus_gallery.html',
     'AccessLoop browser checks: keyboard focus, 320 px reflow, text spacing, closed details opened', responsive_focus),
    ('B14 Account statement: duplicate main, empty header', 'examples/samples/13_statement_layout.html',
     'Two main landmarks and a header cell that labels no data: reviewer decides, fix verified', statement_layout),
    ('B15 Agent mode on the legacy portal', 'examples/samples/08_legacy_portal_gallery.html',
     'One run: the agent fixes what its policy allows, verifies each change and hands the rest to a person', agent_mode),
    ('B6 Accessible sign-in', 'examples/samples/06_accessible_login.html', 'Clean control page; no false positives / edits', accessible),
    ('B7 Unsafe payment page', 'examples/samples/07_unsafe_payment_page.html', 'Script + inline handler refused at input', unsafe),
]


def to_markdown(results: list[CaseResult]) -> str:
    from .fixers import FIXERS
    verified = {a['rule'] for r in results for a in r.applied if a['status'] == 'verified'}
    missing = sorted(set(FIXERS) - verified)
    lines = ['# AccessLoop sample-suite results', '',
             f'**{sum(r.passed for r in results)}/{len(results)} cases passed** '
             '(real Chromium + axe-core, no fake scanner)', '',
             f'**Fix templates proven in a real browser: {len(set(FIXERS) & verified)}/{len(FIXERS)} rule types** '
             '(each applied, re-scanned and verified at least once).' + (f' Not yet exercised: {", ".join(missing)}.' if missing else ''),
             '']
    for r in results:
        lines += [f'## {"PASS" if r.passed else "FAIL"} - {r.name}', f'`{r.file}` - {r.purpose}', '']
        if r.baseline or r.final:
            lines.append(f'- Baseline counts: `{r.baseline}`  ->  Final counts: `{r.final}`')
        for a in r.applied:
            lines.append(f'- {a["status"]}: **{a["rule"]}** `{a["selector"]}`  `{a["before"]}` -> `{a["after"]}`')
        if r.manual_queue:
            lines.append(f'- Manual-review queue: {", ".join(f"`{m}`" for m in r.manual_queue)}')
        if r.note:
            lines.append(f'- Note: {r.note}')
        for label, ok in r.checks:
            lines.append(f'  - [{"x" if ok else " "}] {label}')
        lines.append('')
    return '\n'.join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='sample_results')
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = [run_case(n, f, p, b, out) for n, f, p, b in CASES]
    md = to_markdown(results)
    (out / 'RESULTS.md').write_text(md, encoding='utf-8')
    (out / 'results.json').write_text(json.dumps([r.__dict__ for r in results], indent=2, default=str), encoding='utf-8')
    print(md)
    return 0 if all(r.passed for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
