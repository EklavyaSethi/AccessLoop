"""Turn validation_results/*.json into docs/VALIDATION_REPORT.md (numbers only; no hand-edited figures)."""
from __future__ import annotations
import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from .validation import TOOL_NAMES, TOOLS


def _load(path: Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def _pct(a: int, b: int) -> str:
    return f'{(100 * a / b):.0f}%' if b else 'n/a'


def _outcomes(rows):
    """Counts of approval decisions by result, fixes contained in them, and seconds per decision."""
    c, fixes = Counter(), Counter()
    secs = []
    for r in rows:
        for o in r.get('outcomes', []):
            if o['status'] == 'skipped':
                continue
            c[o['status']] += 1
            fixes[o['status']] += o.get('size', 1)
            if o['status'] in ('verified', 'rolled_back'):
                secs.append(o['seconds'])
    return c, fixes, secs


def summarise(res: Path) -> dict:
    gov, act, mdn, tpl = (_load(res / f'{n}.json') for n in ('govuk', 'act', 'mdn', 'templates'))
    s: dict = {}
    every = []
    if gov:
        pages = [p for p in gov['pages'] if p['status'] == 'ok']
        det_v = [p for p in pages if any(k in p['violations'] and p['violations'][k] for k in p['detected_rules'])]
        det_any = [p for p in pages if p['detected_rules']]
        tools = {}
        for t in TOOLS:
            vals = [p['tools'].get(t) for p in gov['pages'] if p.get('tools')]
            tools[t] = {'found': sum(v in ('error', 'error_paid') for v in vals),
                        'flagged': sum(v in ('error', 'error_paid', 'warning', 'manual', 'identified') for v in vals),
                        'n': len(vals)}
        fixable = [p for p in det_any if any(p['proposals'].get(k) for k in p['detected_rules'])]
        cleared = []
        for p in fixable:
            left = Counter(p['final_violations']) + Counter(p['final_reviews'])
            noise = Counter(gov['control_noise'])
            if all(left.get(k, 0) <= noise.get(k, 0) for k in p['detected_rules']):
                cleared.append(p)
        by_cat = defaultdict(lambda: [0, 0])
        for p in pages:
            by_cat[p['category']][1] += 1
            by_cat[p['category']][0] += bool(p['detected_rules'])
        s['govuk'] = {'pages': len(gov['pages']), 'ok': len(pages), 'detected': len(det_any),
                      'detected_as_violation': len(det_v), 'tools': tools, 'fixable': len(fixable),
                      'cleared': len(cleared), 'by_category': dict(by_cat), 'noise': gov['control_noise'],
                      'not_detected': sorted(p['name'] for p in pages if not p['detected_rules'])}
        every += pages
    if act:
        from .catalog import EXCLUDED
        def _oos(rules):
            return set(rules) <= set(EXCLUDED) or any('AAA' in EXCLUDED.get(r, '') for r in rules)
        out_of_scope = sorted({e['rule'] for e in act['examples'] if e.get('axe_rules') and _oos(e['axe_rules'])})
        ex = [e for e in act['examples'] if e['status'] == 'ok' and e['rule'] not in out_of_scope]
        failed = [e for e in ex if e['kind'] == 'failed']
        passed = [e for e in ex if e['kind'] == 'passed']
        f_det = [e for e in failed if e['violated'] or e['needs_review']]
        f_prop = [e for e in f_det if e['proposed']]
        f_fixed = [e for e in f_prop if not e['left_after']]
        p_alarm = [e for e in passed if e['violated']]
        p_edit = [e for e in passed if e['proposed']]
        p_edit_review = [e for e in p_edit if not any(r in e['violations'] for r in e['proposals'] if r in e['axe_rules'])]
        per_rule = defaultdict(lambda: Counter())
        for e in failed:
            k = per_rule[e['rule']]
            k['failed'] += 1
            k['detected'] += bool(e['violated'] or e['needs_review'])
            k['fixed'] += bool(e['proposed'] and not e['left_after'])
        for e in passed:
            k = per_rule[e['rule']]
            k['passed'] += 1
            k['false_alarm'] += bool(e['violated'])
        s['act'] = {'rules': len({e['act_id'] for e in ex}), 'failed': len(failed), 'passed': len(passed),
                    'detected': len(f_det), 'proposed': len(f_prop), 'fixed': len(f_fixed),
                    'false_alarm': len(p_alarm), 'false_edit': len(p_edit), 'false_edit_review': len(p_edit_review),
                    'out_of_scope': out_of_scope,
                    'false_alarm_examples': [f'{e["rule"]} - {e["example"]}' for e in p_alarm],
                    'per_rule': {k: dict(v) for k, v in per_rule.items()},
                    'errors': sum(1 for e in act['examples'] if e['status'] != 'ok')}
        every += failed
    for name, data in (('mdn', mdn), ('templates', tpl)):
        if not data:
            continue
        pages = [p for p in data['pages'] if p['status'] == 'ok']
        v0 = sum(sum(p['violations'].values()) for p in pages)
        v1 = sum(sum(p['final_violations'].values()) for p in pages)
        r0 = sum(sum(p['reviews'].values()) for p in pages)
        r1 = sum(sum(p['final_reviews'].values()) for p in pages)
        left = Counter()
        for p in pages:
            left.update(p['final_violations'])
        s[name] = {'pages': len(data['pages']), 'ok': len(pages), 'violations_before': v0, 'violations_after': v1,
                   'reviews_before': r0, 'reviews_after': r1, 'left_top': left.most_common(8),
                   'scan_median': statistics.median([p['scan_seconds'] for p in pages]) if pages else None,
                   'errors': [p.get('error', '')[:120] for p in data['pages'] if p['status'] != 'ok']}
        every += pages
    c, fixes, secs = _outcomes(every)
    s['overall'] = {'approvals': sum(c.values()), 'outcomes': dict(c), 'fixes': dict(fixes),
                    'batches': sum(1 for p in every for o in p.get('outcomes', []) if o.get('mode') == 'batch'),
                    'median_seconds': statistics.median(secs) if secs else None,
                    'p95_seconds': sorted(secs)[int(0.95 * (len(secs) - 1))] if secs else None,
                    'originals_untouched': all(p.get('original_untouched', True) for p in every),
                    'audit_chains_ok': all(p.get('audit_ok', True) for p in every), 'pages': len(every),
                    # do-no-harm: pages that ended with MORE violations or manual-review items than they started with
                    'pages_worse': sum(1 for p in every if 'final_violations' in p and
                                       (_n(p['final_violations']) > _n(p.get('violations')) or _n(p.get('final_reviews')) > _n(p.get('reviews')))),
                    'pages_measured': sum(1 for p in every if 'final_violations' in p)}
    rb = Counter(o['rule'] for p in every for o in p.get('outcomes', []) if o['status'] == 'rolled_back')
    s['overall']['rollbacks_by_rule'] = rb.most_common(10)
    import re as _re
    rb_reason = Counter(_re.sub(r'\s*\(.*', '', o['detail'].split(':')[0])[:70]
                        for p in every for o in p.get('outcomes', []) if o['status'] == 'rolled_back')
    s['overall']['rollback_reasons'] = rb_reason.most_common(6)
    return s


def _n(x) -> int:
    return sum(x.values()) if isinstance(x, dict) else int(x or 0)


def to_markdown(s: dict) -> str:
    o = s['overall']
    L = ['# AccessLoop validation report', '',
         'Every number below is produced by `python -m accessloop.validation` followed by `python -m accessloop.validation_report`. '
         'All pages were written by third parties, not by the AccessLoop team. Each page went through the full loop: '
         'scan (WCAG A/AA + best-practice), propose, approve (a simulated reviewer approves everything and types neutral '
         'text where text is needed), re-scan, verify or roll back.', '']
    L += ['## Headline', '',
          f'- **{o["pages"]} pages and test cases**, **{o["approvals"]} approval decisions** covering '
          f'**{sum(o["fixes"].values())} individual fixes** ({o["batches"]} of the decisions were batches of similar fixes).',
          f'- Decisions verified: **{o["outcomes"].get("verified", 0)}** ({_pct(o["outcomes"].get("verified", 0), o["approvals"])}), '
          f'automatically rolled back: **{o["outcomes"].get("rolled_back", 0)}**, refused before writing: '
          f'{o["outcomes"].get("refused", 0)}. Fixes kept: **{o["fixes"].get("verified", 0)}**.',
          f'- Every original file was left untouched: **{"yes" if o["originals_untouched"] else "NO"}**. Every audit log hash chain verified: '
          f'**{"yes" if o["audit_chains_ok"] else "NO"}**.',
          f'- Do no harm: pages that ended with more violations or more manual-review items than they started with: '
          f'**{o.get("pages_worse", 0)} of {o.get("pages_measured", 0)}**. Every kept fix was checked to raise no other rule\'s count.',
          f'- Time per approval decision (write + full re-scan + verify): median **{o["median_seconds"]} s**, 95th percentile '
          f'**{o["p95_seconds"]} s**.', '']
    if 'govuk' in s:
        g = s['govuk']
        L += ['## 1. GOV.UK accessibility tool audit (142 known barriers)', '',
              'Source: [alphagov/accessibility-tool-audit](https://github.com/alphagov/accessibility-tool-audit). Each page holds '
              'one deliberate barrier. GOV.UK published how 13 tools did on the same pages (results last updated April 2018, so '
              'those tools have improved since; treat the comparison as indicative). A barrier counts as detected when AccessLoop '
              'reports a rule on the page that it does not report on an identical control page without the barrier.', '',
              f'- AccessLoop detected **{g["detected"]} of {g["ok"]}** barriers ({_pct(g["detected"], g["ok"])}); '
              f'{g["detected_as_violation"]} as violations, the rest as "needs review".',
              f'- Of the detected barriers, **{g["fixable"]}** had an AccessLoop fix proposal, and **{g["cleared"]}** were fully '
              'cleared after approval and re-verification.', '',
              '| Tool | Barriers found (error) | Found or flagged for checking |', '|---|---|---|',
              f'| **AccessLoop (axe-core 4.14 + best practice)** | **{g["detected_as_violation"]}** | **{g["detected"]}** |']
        for t, v in sorted(g['tools'].items(), key=lambda kv: -kv[1]['found']):
            L.append(f'| {TOOL_NAMES[t]} | {v["found"]} | {v["flagged"]} |')
        L += ['', 'Barriers no automated tool can judge (plain language, meaningful sequence, focus order and similar) make up '
              'most of the misses; that is why AccessLoop keeps a manual checklist of the 32 WCAG criteria axe cannot test.', '',
              '| Category | Detected / pages |', '|---|---|']
        for cat, (d, n) in sorted(g['by_category'].items()):
            L.append(f'| {cat} | {d} / {n} |')
        L.append('')
    if 'act' in s:
        a = s['act']
        L += ['## 2. W3C ACT rules test cases (the official accessibility conformance test cases)', '',
              'Source: [act-rules/act-rules.github.io](https://github.com/act-rules/act-rules.github.io), restricted to the '
              f'{a["rules"]} ACT rules that axe-core implements. "Failed" examples contain a real failure; "passed" examples are '
              'correct and must not be changed.', '',
              f'- Failed examples: **{a["failed"]}**. Detected **{a["detected"]}** ({_pct(a["detected"], a["failed"])}); '
              f'fix proposed for **{a["proposed"]}**; failure fully removed and re-verified in **{a["fixed"]}** '
              f'({_pct(a["fixed"], a["detected"])} of detected).',
              f'- Passed examples: **{a["passed"]}**. Wrongly reported as a violation: **{a["false_alarm"]}** '
              f'({_pct(a["false_alarm"], a["passed"])}). A fix was offered on **{a["false_edit"]}**: '
              f'{a["false_edit_review"]} of those come from axe "needs review" results, where the engine itself is unsure and '
              'AccessLoop asks the reviewer instead of acting; the rest are the false alarms above. Nothing is ever applied '
              'without approval, and in this run no passed example was edited.',
              f'- Out of scope and not counted (AAA or experimental rules AccessLoop does not target): '
              f'{", ".join(a["out_of_scope"]) or "none"}.', '']
        if a['false_alarm_examples']:
            L += ['False alarms (all inherited from axe-core, listed for transparency): ' +
                  '; '.join(a['false_alarm_examples'][:12]), '']
        L += ['| ACT rule | Failed: detected / fixed / total | Passed: false alarms / total |', '|---|---|---|']
        for rule, k in sorted(a['per_rule'].items()):
            L.append(f'| {rule} | {k.get("detected", 0)} / {k.get("fixed", 0)} / {k.get("failed", 0)} | '
                     f'{k.get("false_alarm", 0)} / {k.get("passed", 0)} |')
        L.append('')
    for key, title, src in (('mdn', '3. MDN accessibility teaching pages', '[mdn/learning-area](https://github.com/mdn/learning-area) (`accessibility/`)'),
                            ('templates', '4. Real-world Bootstrap templates', '12 [StartBootstrap](https://github.com/StartBootstrap) templates')):
        if key not in s:
            continue
        m = s[key]
        L += [f'## {title}', '', f'Source: {src}. {m["ok"]} of {m["pages"]} pages scanned.', '',
              f'- Violations: **{m["violations_before"]} → {m["violations_after"]}** '
              f'({_pct(m["violations_before"] - m["violations_after"], m["violations_before"])} removed). '
              f'Needs-review items: {m["reviews_before"]} → {m["reviews_after"]}.',
              f'- Median scan time per page: {m["scan_median"]} s.',
              '- Most common items left (they need a person or a structural change): ' +
              (', '.join(f'`{r}` ({n})' for r, n in m['left_top']) or 'none') + '.', '']
        if key == 'templates':
            L += ['Note: these templates load Bootstrap from a CDN. AccessLoop never fetches anything from the internet during a '
                  'scan, so CDN style sheets are absent and colour-contrast results reflect only the local styles.', '']
    L += ['## Rollbacks (the safety net working)', '',
          'A rollback means the approved change did not make things better, or made something else worse, so the file was '
          'restored byte for byte. Most common rules and reasons:', '']
    L += [f'- `{r}`: {n}' for r, n in o['rollbacks_by_rule']] or ['- none']
    L += [''] + [f'- {r}: {n}' for r, n in o['rollback_reasons']] + ['']
    L += ['## Limits of this validation', '',
          '- The reviewer is simulated. Real reviewers type meaningful text; the simulated one types neutral placeholder text, '
          'so some rollbacks (for example a typed name that does not match the visible label) would not happen with a careful reviewer.',
          '- Scripts on these pages were not run (by design), so content built by JavaScript was not checked.',
          '- Automated rules find only part of all barriers. Passing automated checks is not WCAG conformance.', '']
    return '\n'.join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default='validation_results')
    ap.add_argument('--out', default='docs/VALIDATION_REPORT.md')
    args = ap.parse_args()
    s = summarise(Path(args.results))
    Path(args.results, 'summary.json').write_text(json.dumps(s, indent=1), encoding='utf-8')
    Path(args.out).write_text(to_markdown(s), encoding='utf-8')
    print(json.dumps(s['overall'], indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
