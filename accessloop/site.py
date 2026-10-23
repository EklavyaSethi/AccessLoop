"""Site scan: many pages at once, issues grouped by shared template, and optional unattended automatic fixing.

Pages that share a header, footer or form template usually share its problems. Grouping identical problems across pages
(same rule, same element markup) shows where fixing one template fixes many pages.
"""
from __future__ import annotations
import io
import json
import re
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

from .exports import git_patch
from .planner import plan
from .workflow import Workflow, WorkflowError, approve_all

MAX_PAGES = 200


def signature(html_snippet: str) -> str:
    """A stable fingerprint of an element's markup: tag, id and classes plus a short normalised text."""
    s = re.sub(r'\s+', ' ', html_snippet or '').strip()
    m = re.match(r'<([a-zA-Z0-9-]+)([^>]*)>', s)
    if not m:
        return s[:80]
    attrs = m.group(2)
    keep = ' '.join(re.findall(r'\b(?:id|class|name|type|role|href)\s*=\s*"[^"]*"', attrs))
    return f'<{m.group(1).lower()}{" " + keep if keep else ""}>'[:140]


def read_upload(name: str, data: bytes) -> list[tuple[str, str]]:
    """HTML files from an uploaded .html or .zip (only .html/.htm entries; nested folders kept in the name)."""
    if name.lower().endswith('.zip'):
        out = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir() or not info.filename.lower().endswith(('.html', '.htm')) or info.file_size > 2 * 1024 * 1024:
                    continue
                if '..' in Path(info.filename).parts or info.filename.startswith('/'):
                    continue
                out.append((info.filename, z.read(info).decode('utf-8', errors='replace')))
                if len(out) >= MAX_PAGES:
                    break
        return out
    return [(name, data.decode('utf-8', errors='replace'))]


def scan_site(pages: list[tuple[str, str]], best_practice: bool = True, extended: bool = False,
              allow_scripts: bool = True, fix: bool = False, reviewer: str = 'site scan', progress=None) -> dict:
    """Scan (and optionally auto-fix) every page. Returns per-page rows, template groups and, when fixing, the files."""
    rows, groups = [], defaultdict(lambda: {'pages': set(), 'count': 0, 'fixable': False, 'impact': '', 'help': ''})
    files: dict[str, str] = {}
    for i, (name, html) in enumerate(pages[:MAX_PAGES]):
        if progress:
            progress(i, len(pages), name)
        with tempfile.TemporaryDirectory() as tmp:
            engine = Workflow(Path(tmp))
            try:
                engine.load(html, allow_scripts=allow_scripts)
                scan = engine.scan(best_practice=best_practice, extended=extended)
            except Exception as error:  # noqa: BLE001 - one bad page never stops the site scan
                rows.append({'page': name, 'status': 'refused' if isinstance(error, WorkflowError) else 'error',
                             'error': str(error)[:200]})
                continue
            fixable_idx = {p.finding_index: p for p in plan(engine.current_html, scan.items)}
            for idx, f in enumerate(scan.items):
                key = (f.rule_id, signature(f.html))
                g = groups[key]
                g['pages'].add(name)
                g['count'] += 1
                g['fixable'] = g['fixable'] or idx in fixable_idx
                g['impact'], g['help'], g['kind'] = f.impact, f.help, f.kind
            row = {'page': name, 'status': 'scanned', 'violations': len(scan.findings), 'needs_review': len(scan.reviews),
                   'fixable': len(engine.proposals)}
            if fix:
                outcomes = approve_all(engine, lambda p: None, reviewer=reviewer)
                row['fixed'] = sum(o['size'] for o in outcomes if o['status'] == 'verified')
                row['rolled_back'] = sum(1 for o in outcomes if o['status'] == 'rolled_back')
                row['violations_after'] = len(engine.current_scan.findings)
                files[name] = engine.current_html
                patch = git_patch(html, engine.current_html, name, reviewer)
                if patch:
                    files[name + '.patch'] = patch
                files[name + '.audit.jsonl'] = (Path(tmp) / 'audit.jsonl').read_text(encoding='utf-8')
            rows.append(row)
    template = []
    for (rule, sig), g in groups.items():
        template.append({'rule': rule, 'element': sig, 'pages': len(g['pages']), 'occurrences': g['count'],
                         'impact': g['impact'], 'help': g['help'], 'fix_available': g['fixable'],
                         'likely_shared_template': len(g['pages']) >= 2, 'kind': g.get('kind', 'violation'),
                         'example_pages': sorted(g['pages'])[:5]})
    template.sort(key=lambda t: (-t['pages'], -t['occurrences'], t['rule']))
    return {'pages': rows, 'groups': template, 'files': files}


def result_zip(result: dict) -> bytes:
    """Repaired pages, patches, audit logs and a summary, in one zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, text in result['files'].items():
            z.writestr(f'repaired/{name}', text)
        z.writestr('summary.json', json.dumps({'pages': result['pages'], 'groups': result['groups']}, indent=1))
    return buf.getvalue()
