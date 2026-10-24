"""Measure speed and draft quality on the sample pages, for the deck and the judges.

    python -m accessloop.measure                 # rule-based drafts (no AI)
    python -m accessloop.measure --ai            # AI drafts (needs ACCESSLOOP_AI and its key; consent is given here)

For every sample page: load, scan, let the agent repair it (default policy: low risk only), draft the answers it asks
for, then apply every draft exactly as drafted and count how many verify. Applying drafts unread is NOT how AccessLoop
is meant to be used (a person reviews each one); here it measures how often a draft would pass the engine's checks
as-is. Whether a draft is the RIGHT description is a human judgement that no script can make.

Writes docs/MEASUREMENTS.md and validation_results/measurements[_ai].json.
"""
from __future__ import annotations
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(use_ai: bool = False) -> dict:
    from .web.server import Session
    from . import ai_advisor
    from .workflow import WorkflowError
    pages, refused = [], []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / 'examples').symlink_to(ROOT / 'examples')
        for sample in Session(work).samples():
            s = Session(work)
            row = {'page': Path(sample['id']).name}
            t0 = time.perf_counter()
            try:
                s.load(None, '', sample=sample['id'])
            except WorkflowError as error:          # e.g. the deliberately unsafe sample page: refused by design
                refused.append({'page': row['page'], 'why': str(error)})
                print(f"{row['page']:<40} refused by the input check (by design): {error}", flush=True)
                continue
            s.scan('en', best_practice=True)
            row['scan_s'] = round(time.perf_counter() - t0, 2)
            t1 = time.perf_counter()
            run_ = s.run_agent(['low'], 200, 'Measurement script', 'en', ai_drafts=False)
            row['agent_s'] = round(time.perf_counter() - t1, 2)
            row.update({'violations_before': run_['before'], 'violations_after': run_['after'], 'fixes_kept': run_['applied'],
                        'rolled_back': run_['rolled_back'], 'questions': len(run_['questions']), 'held': len(run_['held'])})
            t2 = time.perf_counter()
            drafts = s.draft_answers(consent=use_ai, reviewer='Measurement script') if run_['questions'] else {}
            row['draft_s'] = round(time.perf_counter() - t2, 2)
            row['drafts'] = len(drafts)
            row['drafts_ai'] = sum(1 for d in drafts.values() if d.get('_source') == 'ai')
            answers = []
            for key, d in drafts.items():
                rule, selector, line = key.split('|', 2)
                answers.append({'rule': rule, 'selector': selector, 'line': int(line) if line.isdigit() else line,
                                'values': {k: v for k, v in d.items() if not k.startswith('_')}})
            results = s.answer(answers, 'en', 'Measurement script') if answers else []
            row['drafts_verified'] = sum(1 for r in results if r['status'] == 'verified')
            row['drafts_rolled_back'] = sum(1 for r in results if r['status'] in ('rolled_back', 'unchanged', 'refused'))
            state = s.state()
            row['violations_final'] = (state.get('outcome') or {}).get('after_count', run_['after'])
            row['total_s'] = round(time.perf_counter() - t0, 2)
            pages.append(row)
            print(f"{row['page']:<40} {row['violations_before']:>3} → {row['violations_after']:>3} → {row['violations_final']:>3}  "
                  f"fixes {row['fixes_kept']:>2}  drafts {row['drafts_verified']}/{row['drafts']} verified  {row['total_s']:.1f}s",
                  flush=True)
    tot = lambda k: sum(r[k] for r in pages)  # noqa: E731
    scan_agent = [r['scan_s'] + r['agent_s'] for r in pages]
    summary = {
        'pages': len(pages), 'ai_provider': ai_advisor.provider() if use_ai else 'off (rule-based)',
        'violations_before': tot('violations_before'), 'violations_after_agent': tot('violations_after'),
        'violations_after_drafts': tot('violations_final'), 'fixes_kept': tot('fixes_kept'), 'rolled_back': tot('rolled_back'),
        'questions': tot('questions'), 'drafts': tot('drafts'), 'drafts_ai': tot('drafts_ai'),
        'drafts_verified': tot('drafts_verified'),
        'draft_pass_rate': round(100 * tot('drafts_verified') / tot('drafts')) if tot('drafts') else None,
        'scan_plus_agent_seconds_median': round(statistics.median(scan_agent), 2),
        'scan_plus_agent_seconds_total': round(sum(scan_agent), 1),
        'pages_per_minute': round(60 * len(pages) / sum(scan_agent), 1) if sum(scan_agent) else None,
        'agent_seconds_per_fix': round(tot('agent_s') / tot('fixes_kept'), 2) if tot('fixes_kept') else None,
        'machine': f'{sys.platform}, Python {sys.version.split()[0]}',
    }
    summary['refused_unsafe_pages'] = len(refused)
    return {'summary': summary, 'pages': pages, 'refused': refused}


def to_markdown(res: dict, title: str) -> str:
    s = res['summary']
    lines = [f'## {title}', '',
             f"Machine: {s['machine']}. AI: {s['ai_provider']}. Scan: WCAG A/AA plus best-practice rules. Agent policy: low risk only (default).", '',
             '| Measure | Result |', '|---|---|',
             f"| Sample pages measured (+ refused as unsafe, by design) | {s['pages']} (+ {s.get('refused_unsafe_pages', 0)}) |",
             f"| Violation nodes: before → after agent → after drafts applied | {s['violations_before']} → {s['violations_after_agent']} → {s['violations_after_drafts']} |",
             f"| Fixes kept by the agent (each verified by a re-scan) / rolled back | {s['fixes_kept']} / {s['rolled_back']} |",
             f"| Fixes handed to a person (need words) | {s['questions']} |",
             f"| Drafts produced / verified when applied exactly as drafted | {s['drafts']} / {s['drafts_verified']} ({s['draft_pass_rate']}%) |",
             f"| Scan + agent time per page (median) | {s['scan_plus_agent_seconds_median']} s |",
             f"| Throughput (scan + agent, one process) | {s['pages_per_minute']} pages per minute |",
             f"| Agent time per verified fix | {s['agent_seconds_per_fix']} s |", '',
             '| Page | Violations before → after agent → after drafts | Fixes kept | Drafts verified | Seconds |',
             '|---|---|---|---|---|']
    for r in res['pages']:
        lines.append(f"| {r['page']} | {r['violations_before']} → {r['violations_after']} → {r['violations_final']} | "
                     f"{r['fixes_kept']} | {r['drafts_verified']}/{r['drafts']} | {r['total_s']} |")
    lines += ['', 'A draft that verifies passed the engine\'s checks (the problem is gone, nothing else got worse). Whether '
              'it is the right description still needs a person, which is why AccessLoop never applies drafts on its own.', '']
    return '\n'.join(lines)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    use_ai = '--ai' in argv
    res = run(use_ai)
    out = ROOT / 'validation_results' / ('measurements_ai.json' if use_ai else 'measurements.json')
    out.write_text(json.dumps(res, indent=1), encoding='utf-8')
    md_path = ROOT / 'docs' / 'MEASUREMENTS.md'
    head = ('# Measurements\n\nProduced by `python -m accessloop.measure` (rule-based drafts) and '
            '`python -m accessloop.measure --ai` (AI drafts). Re-run them on your own machine; numbers depend on hardware.\n\n')
    sections = {}
    for name, label in (('measurements.json', 'Rule-based drafts (no AI)'), ('measurements_ai.json', 'AI drafts')):
        p = ROOT / 'validation_results' / name
        if p.exists():
            sections[label] = to_markdown(json.loads(p.read_text(encoding='utf-8')), label)
    md_path.write_text(head + '\n'.join(sections.values()), encoding='utf-8')
    print(json.dumps(res['summary'], indent=1))
    print(f'Wrote {out.relative_to(ROOT)} and docs/MEASUREMENTS.md')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
