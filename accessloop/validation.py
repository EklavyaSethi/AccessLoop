"""Independent validation: run AccessLoop's full scan → propose → approve → re-verify loop over third-party pages.

Corpora (not shipped; fetch them first, see docs/VALIDATION_REPORT.md):
  govuk     alphagov/accessibility-tool-audit  142 pages, one known barrier each, with published results for 13 tools
  act       act-rules/act-rules.github.io       W3C ACT test cases: "failed" examples must be caught and fixed,
                                                "passed" examples must not be edited
  mdn       mdn/learning-area (accessibility/)  MDN's teaching pages, including bad/good pairs and a before/after site
  templates StartBootstrap templates            real-world Bootstrap pages (CDN style sheets cannot load offline)

    python -m accessloop.validation --corpora /path/to/corpus --out validation_results

The "reviewer" here is simulated: typed fields get neutral text (or the visible text where the page already shows
it), which is exactly what a hurried reviewer might do. Every approved change is still re-scanned and verified.
"""
from __future__ import annotations
import argparse
import html as html_std
import json
import re
import statistics
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

from .sample_suite import typed_values
from .workflow import Workflow, WorkflowError, approve_all, read_source

TOOLS = ['axe', 'wave', 'sortsite', 'asqatasun', 'tenon', 'codesniffer', 'achecker', 'siteimprove', 'fae', 'aslint',
         'google', 'eiii', 'nu']
TOOL_NAMES = {'axe': 'axe (2017-18 run)', 'wave': 'WAVE', 'sortsite': 'SortSite', 'asqatasun': 'Asqatasun',
              'tenon': 'Tenon', 'codesniffer': 'HTML_CodeSniffer', 'achecker': 'AChecker', 'siteimprove': 'Siteimprove',
              'fae': 'FAE', 'aslint': 'ASLint', 'google': 'Google ADT', 'eiii': 'EIII', 'nu': 'Nu HTML Checker'}
REVIEWER = {'aria-hidden-focus': {'choice': 'unfocus'}, 'meta-refresh': {'choice': 'remove'},
            'video-caption': {'src': 'media/captions.en.vtt'}, 'aria-required-attr': {'aria-checked': 'false'}}


def run_page(source: str, assets_dir: Path | None = None, best_practice: bool = True, limit: int = 400,
             approve: bool = True) -> dict:
    """One page through the whole loop. Returns counts before/after, proposals and every outcome."""
    out: dict = {'status': 'ok'}
    with tempfile.TemporaryDirectory() as tmp:
        engine = Workflow(Path(tmp))
        t0 = time.perf_counter()
        try:
            engine.load(source, allow_scripts=True, assets_dir=assets_dir)
            scan = engine.scan(best_practice=best_practice)
        except (WorkflowError, Exception) as error:  # noqa: BLE001 - recorded per page
            return {'status': 'error', 'error': str(error)[:300]}
        out['scan_seconds'] = round(time.perf_counter() - t0, 2)
        out['violations'] = dict(scan.counts())
        out['reviews'] = dict(scan.review_counts())
        out['proposals'] = Counter(p.rule_id for p in engine.proposals)
        out['proposal_modes'] = Counter('input' if p.needs_input else 'auto' for p in engine.proposals)
        outcomes = approve_all(engine, lambda p: typed_values(p, REVIEWER), reviewer='validation run',
                               limit=limit) if approve else []
        final = engine.current_scan
        out['outcomes'] = outcomes
        out['final_violations'] = dict(final.counts()) if final else {}
        out['final_reviews'] = dict(final.review_counts()) if final else {}
        out['audit_ok'] = engine.audit_status()['verified']
        out['original_untouched'] = (Path(tmp) / 'original.html').read_text(encoding='utf-8') == source
    return out


# ---- corpus: GOV.UK accessibility tool audit ---------------------------------------------------------------------
def govuk(root: Path, log) -> dict:
    tests = json.loads((root / 'tests.json').read_text(encoding='utf-8'))
    by_name = {}
    for cat, group in tests.items():
        for name, info in group.items():
            by_name[html_std.unescape(name).strip()] = (cat, info)
    pages = sorted((root / 'tests').glob('*.html'))
    sample = read_source(pages[0])
    control_src = re.sub(r'<main>.*</main>', '<main><p>Control page.</p></main>', sample, flags=re.S)
    control = run_page(control_src, root, approve=False)
    noise = Counter(control.get('violations', {})) + Counter(control.get('reviews', {}))
    rows = []
    for page in pages:
        src = read_source(page)
        h1 = re.search(r'<h1>(.*?)</h1>', src, re.S)
        name = html_std.unescape(h1.group(1)).strip() if h1 else page.stem
        cat, info = by_name.get(name, ('?', {}))
        r = run_page(src, root)
        found = Counter(r.get('violations', {})) + Counter(r.get('reviews', {}))
        extra = {k: v - noise.get(k, 0) for k, v in found.items() if v > noise.get(k, 0)}
        r.update({'file': page.name, 'name': name, 'category': cat, 'tools': info.get('results', {}),
                  'detected_rules': extra})
        rows.append(r)
        log(f'govuk {len(rows)}/{len(pages)} {page.name}: {"DETECTED " + ",".join(extra) if extra else "-"}')
    return {'control_noise': dict(noise), 'pages': rows}


# ---- corpus: W3C ACT rules test cases ---------------------------------------------------------------------------
def _act_examples(md: str) -> list[tuple[str, str, str]]:
    """(kind, title, html) for each Passed/Failed example with exactly one html code block."""
    out = []
    for m in re.finditer(r'^#### ((Passed|Failed) Example \d+)\s*\n(.*?)(?=^#### |^### |\Z)', md, re.S | re.M):
        blocks = re.findall(r'```html[^\n]*\n(.*?)```', m.group(3), re.S)
        if len(blocks) == 1:
            out.append((m.group(2).lower(), m.group(1), blocks[0]))
    return out


def _wrap(snippet: str) -> str:
    if re.search(r'<html[\s>]', snippet, re.I):
        return snippet
    return ('<!DOCTYPE html>\n<html lang="en">\n<head><meta charset="utf-8"><title>ACT test case</title></head>\n'
            f'<body>\n{snippet}\n</body>\n</html>\n')


def act(root: Path, act_map: dict[str, list[str]], log) -> dict:
    rows = []
    for md_path in sorted((root / '_rules').glob('*.md')):
        md = md_path.read_text(encoding='utf-8')
        rid = re.search(r'^id:\s*(\S+)', md, re.M)
        if not rid or rid.group(1) not in act_map:
            continue
        axe_rules = set(act_map[rid.group(1)])
        title = re.search(r'^name:\s*(.+)$', md, re.M).group(1).strip().strip("'\"")
        for kind, ex_title, snippet in _act_examples(md):
            page = _wrap(snippet)
            r = run_page(page, None, approve=(kind == 'failed'))
            if r['status'] != 'ok':
                rows.append({'act_id': rid.group(1), 'rule': title, 'kind': kind, 'example': ex_title, **r})
                continue
            hit_v = {k: v for k, v in r['violations'].items() if k in axe_rules}
            hit_r = {k: v for k, v in r['reviews'].items() if k in axe_rules}
            left = {k: v for k, v in {**r['final_violations'], **r['final_reviews']}.items() if k in axe_rules}
            props = {k: v for k, v in r['proposals'].items() if k in axe_rules}
            rows.append({'act_id': rid.group(1), 'rule': title, 'axe_rules': sorted(axe_rules), 'kind': kind,
                         'example': ex_title, 'scripted': '<script' in snippet.lower(),
                         'violated': bool(hit_v), 'needs_review': bool(hit_r) and not hit_v, 'proposed': bool(props),
                         'left_after': left, **r})
        log(f'act {rid.group(1)} {title}: {sum(1 for x in rows if x["act_id"] == rid.group(1))} examples')
    return {'examples': rows}


# ---- corpora: MDN and templates (whole pages) --------------------------------------------------------------------
def pages_corpus(files: list[Path], base: Path, log, tag: str) -> dict:
    rows = []
    for f in files:
        r = run_page(read_source(f), f.parent)
        r['file'] = f.relative_to(base).as_posix()
        rows.append(r)
        v0 = sum(r.get('violations', {}).values())
        v1 = sum(r.get('final_violations', {}).values())
        log(f'{tag} {len(rows)}/{len(files)} {r["file"]}: {r["status"]} {v0} → {v1}')
    return {'pages': rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpora', required=True)
    ap.add_argument('--out', default='validation_results')
    ap.add_argument('--only', nargs='*', default=['govuk', 'act', 'mdn', 'templates'])
    args = ap.parse_args()
    base, out = Path(args.corpora), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        print(msg, flush=True)

    if 'govuk' in args.only:
        res = govuk(base / 'accessibility-tool-audit', log)
        (out / 'govuk.json').write_text(json.dumps(res, indent=1, default=dict), encoding='utf-8')
    if 'act' in args.only:
        act_map = json.loads((base / 'act_map.json').read_text(encoding='utf-8'))
        res = act(base / 'act', act_map, log)
        (out / 'act.json').write_text(json.dumps(res, indent=1, default=dict), encoding='utf-8')
    if 'mdn' in args.only:
        files = sorted((base / 'mdn').rglob('*.html'))
        res = pages_corpus(files, base / 'mdn', log, 'mdn')
        (out / 'mdn.json').write_text(json.dumps(res, indent=1, default=dict), encoding='utf-8')
    if 'templates' in args.only:
        files = sorted(p for p in (base / 'templates').rglob('*.html') if 'node_modules' not in p.parts and '/src/' not in p.as_posix())
        res = pages_corpus(files, base / 'templates', log, 'templates')
        (out / 'templates.json').write_text(json.dumps(res, indent=1, default=dict), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
