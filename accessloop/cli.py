"""AccessLoop command line: scan files or folders (text, JSON or SARIF for CI), fix with approval, verify audit logs.

    python -m accessloop scan page.html                      # one page, readable summary
    python -m accessloop scan site/ --format sarif --out a11y.sarif --fail-on serious
    python -m accessloop fix page.html --out fixed.html      # asks before every change (interactive)
    python -m accessloop fix page.html --out fixed.html --approve-auto --reviewer "A. Rao"   # CI: auto fixes only
    python -m accessloop audit verify fixed.audit.jsonl

Exit codes: 0 = nothing at or above --fail-on, 1 = findings at or above --fail-on, 2 = a page was refused or could
not be scanned, 64 = bad command-line usage.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

from . import __version__
from .htmlsource import Doc
from .ledger import verify as verify_ledger
from .models import Finding, ScanResult
from .planner import plan
from .workflow import Workflow, WorkflowError, approve_all, read_source, validate_source

IMPACT_ORDER = ['minor', 'moderate', 'serious', 'critical']
SARIF_LEVEL = {'critical': 'error', 'serious': 'error', 'moderate': 'warning', 'minor': 'note'}
EXIT_OK, EXIT_FINDINGS, EXIT_ERROR, EXIT_USAGE = 0, 1, 2, 64


# ---- scanning ---------------------------------------------------------------------------------------------
def _files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out += sorted(x for x in p.rglob('*') if x.suffix.lower() in {'.html', '.htm'} and x.is_file()
                          and 'node_modules' not in x.parts and not any(part.startswith('.') for part in x.parts))
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError(f'No such file or folder: {raw}')
    return out


def _line_of(doc: Doc, f: Finding) -> int | None:
    el = doc.by_uid.get(f.uid) if f.uid is not None else None
    return doc.source.count('\n', 0, el.start) + 1 if el is not None else None


def scan_file(path: Path, best_practice: bool, scanner=None, allow_scripts: bool = False,
              assets_dir: str | None = None, extended: bool = False) -> dict:
    from .scanner import scan_html
    scanner = scanner or scan_html
    source = read_source(path)
    try:
        validate_source(source, allow_scripts=allow_scripts)
    except WorkflowError as error:
        return {'file': path.as_posix(), 'status': 'refused', 'error': str(error), 'findings': []}
    options: dict = {'best_practice': True} if best_practice else {}
    if scanner is scan_html:
        # The page's own style sheets and images: from --assets-dir, or the page's folder. Nothing outside it is read.
        options['assets_dir'] = Path(assets_dir) if assets_dir else path.parent
        if extended:
            options['extended'] = True
    try:
        result: ScanResult = scanner(source, **options)
    except Exception as error:  # noqa: BLE001 - reported per file, the run continues
        return {'file': path.as_posix(), 'status': 'error', 'error': str(error), 'findings': []}
    doc = Doc(source)
    fixable = {p.finding_index: p for p in plan(source, result.items)}
    findings = []
    for i, f in enumerate(result.items):
        p = fixable.get(i)
        findings.append({'rule': f.rule_id, 'impact': f.impact, 'kind': f.kind, 'selector': f.selector, 'help': f.help,
                         'line': _line_of(doc, f), 'html': f.html[:200],
                         'fix': None if p is None else ('needs reviewer text' if p.needs_input else 'automatic')})
    scripts = bool(re.search(r'<script\b|\son[a-z]+\s*=', source, re.I))
    return {'file': path.as_posix(), 'status': 'scanned', 'findings': findings, 'scripts_not_run': scripts,
            'violations': len(result.findings), 'needs_review': len(result.reviews), 'passed_rules': result.passed_rules}


def _at_or_above(impact: str, threshold: str) -> bool:
    if threshold == 'none':
        return False
    if threshold == 'any':
        return True
    return IMPACT_ORDER.index(impact) >= IMPACT_ORDER.index(threshold) if impact in IMPACT_ORDER else True


def to_sarif(results: list[dict], rules_info: dict) -> dict:
    used = sorted({f['rule'] for r in results for f in r['findings']})
    rules = []
    for rid in used:
        info = rules_info.get(rid, {})
        rules.append({
            'id': rid, 'name': rid,
            'shortDescription': {'text': info.get('title', rid)},
            'fullDescription': {'text': info.get('description', info.get('title', rid))},
            'helpUri': info.get('help_url') or f'https://dequeuniversity.com/rules/axe/4.10/{rid}',
            'properties': {'tags': ['accessibility'] + [f'WCAG {c}' for c in info.get('wcag', [])],
                           'wcagLevel': info.get('level', ''), 'accessloopHandling': info.get('handling', '')},
        })
    index = {r['id']: i for i, r in enumerate(rules)}
    out = []
    for r in results:
        for f in r['findings']:
            region = {'snippet': {'text': f['html']}}
            if f['line']:
                region['startLine'] = f['line']
            text = f['help'].rstrip('.') + '.' + (' axe needs a human to review this.' if f['kind'] == 'review' else '')
            if f['fix']:
                text += f' AccessLoop fix available: {f["fix"]}.'
            out.append({
                'ruleId': f['rule'], 'ruleIndex': index[f['rule']],
                'level': 'note' if f['kind'] == 'review' else SARIF_LEVEL.get(f['impact'], 'warning'),
                'message': {'text': text},
                'locations': [{'physicalLocation': {'artifactLocation': {'uri': r['file']}, 'region': region},
                               'logicalLocations': [{'fullyQualifiedName': f['selector'], 'kind': 'element'}]}],
                'properties': {'impact': f['impact'], 'kind': f['kind'], 'fixAvailable': f['fix'] or 'none'},
            })
    notifications = [{'level': 'error', 'message': {'text': f'{r["file"]}: {r["error"]}'}}
                     for r in results if r['status'] != 'scanned']
    return {
        '$schema': 'https://json.schemastore.org/sarif-2.1.0.json', 'version': '2.1.0',
        'runs': [{
            'tool': {'driver': {'name': 'AccessLoop', 'version': __version__, 'semanticVersion': __version__,
                                'informationUri': 'https://github.com/', 'rules': rules}},
            'results': out,
            'invocations': [{'executionSuccessful': not notifications, 'toolExecutionNotifications': notifications}],
        }],
    }


def _text_report(results: list[dict], threshold: str) -> str:
    lines = []
    for r in results:
        if r['status'] != 'scanned':
            lines.append(f'✗ {r["file"]}: {r["status"].upper()} - {r["error"]}')
            continue
        fixable = sum(1 for f in r['findings'] if f['fix'])
        lines.append(f'• {r["file"]}: {r["violations"]} violation node(s), {r["needs_review"]} needs review, '
                     f'{fixable} with an AccessLoop fix' + (' (scripts present, not run)' if r.get('scripts_not_run') else ''))
        for f in sorted(r['findings'], key=lambda f: (-IMPACT_ORDER.index(f['impact']) if f['impact'] in IMPACT_ORDER else 0,
                                                       f['line'] or 0)):
            mark = '!' if f['kind'] == 'violation' and _at_or_above(f['impact'], threshold) else ' '
            where = f'line {f["line"]}' if f['line'] else f['selector']
            fix = f' [fix: {f["fix"]}]' if f['fix'] else ''
            review = ' (needs review)' if f['kind'] == 'review' else ''
            lines.append(f'   {mark} {f["impact"]:<8} {f["rule"]:<30} {where}{review}{fix}')
    scanned = [r for r in results if r['status'] == 'scanned']
    if len(scanned) > 1:
        from .site import signature
        shared: dict = {}
        for r in scanned:
            for f in r['findings']:
                shared.setdefault((f['rule'], signature(f['html'])), set()).add(r['file'])
        top = sorted(((len(p), k) for k, p in shared.items() if len(p) > 1), reverse=True)[:10]
        if top:
            lines += ['', 'Shared across pages (fix once in the template):']
            lines += [f'   {n:>3} pages  {rule:<28} {sig}' for n, (rule, sig) in top]
    total = Counter(f['impact'] for r in scanned for f in r['findings'] if f['kind'] == 'violation')
    lines += ['', f'{len(results)} page(s): {len(scanned)} scanned, {len(results) - len(scanned)} refused or failed. '
              + 'Violations by severity: ' + (', '.join(f'{k} {total[k]}' for k in reversed(IMPACT_ORDER) if total[k]) or 'none')
              + '.']
    return '\n'.join(lines)


def cmd_scan(args) -> int:
    try:
        files = _files(args.paths)
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return EXIT_USAGE
    if not files:
        print('No .html files found.', file=sys.stderr)
        return EXIT_USAGE
    results = []
    for path in files:
        if not args.quiet and args.format == 'text':
            print(f'Scanning {path} …', file=sys.stderr)
        results.append(scan_file(path, args.best_practice, allow_scripts=args.allow_scripts, assets_dir=args.assets_dir,
                                 extended=args.extended))
    if args.format == 'sarif':
        from .catalog import build
        info = {r['rule_id']: r for r in build()['rules']}
        text = json.dumps(to_sarif(results, info), indent=2, ensure_ascii=False)
    elif args.format == 'junit':
        from .exports import junit_xml
        text = junit_xml(results)
    elif args.format == 'json':
        text = json.dumps({'tool': 'AccessLoop', 'version': __version__, 'best_practice': args.best_practice,
                           'results': results}, indent=2, ensure_ascii=False)
    else:
        text = _text_report(results, args.fail_on)
    if args.out:
        Path(args.out).write_text(text + '\n', encoding='utf-8')
        print(f'Wrote {args.out}', file=sys.stderr)
    else:
        print(text)
    if any(r['status'] != 'scanned' for r in results):
        return EXIT_ERROR
    over = any(f['kind'] == 'violation' and _at_or_above(f['impact'], args.fail_on) for r in results for f in r['findings'])
    return EXIT_FINDINGS if over else EXIT_OK


# ---- fixing -----------------------------------------------------------------------------------------------
def _ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return ''


def _ask_values(p) -> dict | None:
    values: dict = {}
    for fld in p.fields:
        if fld['kind'] == 'select':
            print(f'   {fld["label"]}')
            for i, (v, label) in enumerate(fld['options'], start=1):
                print(f'     {i}. {label}')
            pick = _ask('   Choose a number (blank = skip this fix): ').strip()
            if not pick.isdigit() or not 1 <= int(pick) <= len(fld['options']):
                return None
            values[fld['name']] = fld['options'][int(pick) - 1][0]
        elif fld['kind'] == 'checkbox':
            values[fld['name']] = _ask(f'   {fld["label"]}? [y/N] ').strip().lower() in {'y', 'yes'}
        else:
            text = _ask(f'   {fld["label"]} (blank = skip): ').strip()
            if not text and fld.get('required', True) and not any(f['kind'] == 'checkbox' for f in p.fields):
                return None
            values[fld['name']] = text
    return values


def cmd_fix(args) -> int:
    src = Path(args.file)
    if not src.is_file():
        print(f'No such file: {src}', file=sys.stderr)
        return EXIT_USAGE
    out = Path(args.out)
    if out.resolve() == src.resolve():
        print('Write the repaired page to a new file (--out); the original is never overwritten.', file=sys.stderr)
        return EXIT_USAGE
    if getattr(args, 'agent', False):
        args.approve_auto = True
    interactive = not args.approve_auto
    if interactive and not sys.stdin.isatty() and not args.force_interactive:
        print('No terminal to ask for approval. Use --approve-auto with --reviewer for unattended auto-only fixing.',
              file=sys.stderr)
        return EXIT_USAGE
    typed = (args.reviewer or '').strip()
    if not args.user and (len(typed) < 2 or not any(ch.isalpha() for ch in typed)):
        print('fix needs --reviewer "Your Name" (or --user ACCOUNT): every decision and every agent run is recorded '
              'against the person who made it.', file=sys.stderr)
        return EXIT_USAGE
    reviewer = (args.reviewer or '').strip() or None
    identity = None
    if args.user:
        import getpass
        from . import accounts
        try:
            identity = accounts.login(args.user, os.getenv('ACCESSLOOP_PASSWORD') or getpass.getpass(f'Password for {args.user}: '))
        except accounts.AccountError as error:
            print(error, file=sys.stderr)
            return EXIT_USAGE
        reviewer = identity.label
    with tempfile.TemporaryDirectory() as tmp:
        engine = Workflow(Path(tmp))
        engine.signer = identity
        try:
            engine.load(read_source(src), allow_scripts=args.allow_scripts, assets_dir=src.parent)
            scan = engine.scan(language=args.language, best_practice=args.best_practice, extended=args.extended)
        except Exception as error:  # noqa: BLE001
            print(f'Could not process {src}: {error}', file=sys.stderr)
            return EXIT_ERROR
        print(f'{src}: {len(scan.findings)} violation node(s), {len(scan.reviews)} needs review, '
              f'{len(engine.proposals)} fix proposal(s).')
        decided: set[tuple] = set()
        stats = Counter()
        if getattr(args, 'agent', False):
            from . import agent
            policy = agent.Policy(risks=('low', 'medium') if args.risk == 'medium' else ('low',), max_changes=args.max_changes)
            print('Agent policy: ' + policy.describe())

            def show(line, run):
                t, phase, text = line
                print(f'  {t:6.2f}s {phase:<9} {text}')
            run = agent.run(engine, policy, reviewer=f'AccessLoop agent (policy approved by {reviewer})', language=args.language,
                            on_log=show)
            stats['fixes kept'] += run.applied
            stats['rolled back'] += run.rolled_back
            stats['questions for you'] += len(run.questions)
            stats['held for approval'] += len(run.held)
        elif args.approve_auto:
            for r in approve_all(engine, lambda p: None, reviewer=reviewer, language=args.language):
                key = 'needs your text (skipped)' if r['status'] == 'skipped' else r['status']
                stats[key] += r['size'] if r['status'] == 'verified' else 1
                if r['status'] not in ('verified', 'skipped'):
                    print(f'   {r["rule"]} ({r["mode"]}): {r["status"]}: {r["detail"]}')
        for _ in range(0 if args.approve_auto else 500):
            todo = [p for p in engine.proposals if (p.rule_id, p.selector, p.before) not in decided]
            if not todo:
                break
            p = todo[0]
            decided.add((p.rule_id, p.selector, p.before))
            if args.approve_auto:
                if p.needs_input:
                    stats['needs your text (skipped)'] += 1
                    continue
                values = None
            else:
                print(f'\n[{p.rule_id}] line {p.line}: {p.explanation}\n   evidence: {p.evidence}')
                print(f'   - {p.before[:160]}\n   + {p.after[:160]}')
                if _ask('   Apply this fix? [y/N] ').strip().lower() not in {'y', 'yes'}:
                    engine.reject(p.proposal_id, reviewer)
                    stats['rejected'] += 1
                    continue
                values = _ask_values(p) if p.needs_input else None
                if p.needs_input and values is None:
                    engine.reject(p.proposal_id, reviewer)
                    stats['skipped (no text given)'] += 1
                    continue
            try:
                outcome = engine.apply(p.proposal_id, approved=True, language=args.language, values=values, reviewer=reviewer)
            except WorkflowError as error:
                print(f'   refused: {error}')
                stats['refused'] += 1
                continue
            stats[outcome.status] += 1
            if not args.approve_auto or outcome.status != 'verified':
                print(f'   {outcome.status}: {outcome.detail}')
        out.write_text(engine.current_html, encoding='utf-8', newline='')
        log = out.with_suffix('.audit.jsonl')
        shutil.copyfile(Path(tmp) / 'audit.jsonl', log)
        from .exports import git_patch
        patch = git_patch(read_source(src), engine.current_html, src.name, reviewer or '')
        if patch:
            out.with_suffix('.patch').write_text(patch, encoding='utf-8')
            print(f'Patch for your repository: {out.with_suffix(".patch")} (apply with git am or git apply).')
        final = engine.current_scan
        print(f'\nWrote {out} and its audit log {log}.')
        print('Decisions: ' + (', '.join(f'{k} {v}' for k, v in stats.items()) or 'none') + '.')
        if final is not None:
            print(f'Violations: {len(scan.findings)} → {len(final.findings)}; needs review: {len(scan.reviews)} → {len(final.reviews)}.')
        return EXIT_OK if final is not None and not final.findings else EXIT_FINDINGS


def cmd_issues(args) -> int:
    """Turn what is left on a page into tracker issues: a Jira CSV, GitHub-issue Markdown, or real GitHub issues."""
    import subprocess
    from .exports import _issues, github_issues, jira_csv
    r = scan_file(Path(args.file), not args.wcag_only, allow_scripts=args.allow_scripts)
    if r['status'] != 'scanned':
        print(f'{args.file}: {r["error"]}', file=sys.stderr)
        return EXIT_ERROR
    from .catalog import build
    info = {x['rule_id']: x for x in build()['rules']}
    state = {'source_name': Path(args.file).name, 'unresolved': [
        {'rule': f['rule'], 'impact': f['impact'], 'selector': f['selector'], 'help': f['help'], 'kind': f['kind'],
         'wcag': info.get(f['rule'], {}).get('wcag', []), 'help_url': info.get(f['rule'], {}).get('help_url', ''),
         'handling_label': 'fix needs reviewer text' if f['fix'] else info.get(f['rule'], {}).get('handling', ''),
         'description': f'line {f["line"]}' if f['line'] else ''} for f in r['findings'] if f['fix'] != 'automatic']}
    if args.jira:
        Path(args.jira).write_text(jira_csv(state), encoding='utf-8')
        print(f'Wrote {args.jira} ({len(state["unresolved"])} issues). Import it in Jira: Settings > System > External System Import > CSV.')
    if not args.github:
        print(github_issues(state))
        return EXIT_OK
    issues = _issues(state)
    if not args.create:
        print(f'{len(issues)} issue(s) would be created in {args.github}. Add --create to file them with the GitHub CLI.')
        return EXIT_OK
    made = 0
    for i in issues:
        title = f'[a11y] {i["help"]} ({state["source_name"]})'
        body = (f'Element: `{i["selector"]}`\nRule: `{i["rule"]}`, WCAG {", ".join(i["wcag"]) or "best practice"}, '
                f'impact {i["impact"]}\nGuidance: {i["url"]}\n\nFiled by AccessLoop.')
        res = subprocess.run(['gh', 'issue', 'create', '-R', args.github, '--title', title, '--body', body,
                              '--label', 'accessibility'], capture_output=True, text=True)
        if res.returncode != 0:
            print(f'gh failed: {res.stderr.strip()[:300]}', file=sys.stderr)
            return EXIT_ERROR
        made += 1
        print(res.stdout.strip())
    print(f'Created {made} issue(s) in {args.github}.')
    return EXIT_OK


def cmd_template(args) -> int:
    """Fix a server-side template: scan its rendered output, apply automatic fixes there, carry them into the template."""
    from .templates import TemplateError, fix_template, load_context
    src = Path(args.template)
    if not src.is_file():
        print(f'No such file: {src}', file=sys.stderr)
        return EXIT_USAGE
    if not (args.reviewer or '').strip():
        print('--reviewer NAME is required: every approval is recorded against a person.', file=sys.stderr)
        return EXIT_USAGE
    try:
        rendered = read_source(Path(args.rendered)) if args.rendered else None
        result = fix_template(src, rendered=rendered, context=load_context(args.context), reviewer=args.reviewer,
                              best_practice=not args.wcag_only)
    except (TemplateError, WorkflowError, OSError, ValueError) as error:
        print(f'Could not fix {src}: {error}', file=sys.stderr)
        return EXIT_ERROR
    out = Path(args.out)
    if out.resolve() == src.resolve():
        print('Write the fixed template to a new file (--out).', file=sys.stderr)
        return EXIT_USAGE
    out.write_text(result['template'], encoding='utf-8')
    out.with_suffix(out.suffix + '.audit.jsonl').write_text(result['audit'], encoding='utf-8')
    from .exports import git_patch
    patch = git_patch(read_source(src), result['template'], src.name, args.reviewer)
    if patch:
        out.with_suffix(out.suffix + '.patch').write_text(patch, encoding='utf-8')
    print(f'Rendered page: {result["violations_before"]} → {result["violations_after_rendered"]} violation node(s).')
    for c in result['carried']:
        print(f'  carried into the template: {c["rule"]} ({c["edits"]} edit(s))')
    for m in result['manual']:
        for ch in m['changes']:
            print(f'  MANUAL in template: {m["rule"]}: "{ch["before"]}" → "{ch["after"]}"  near: …{ch["context"][-80:]}')
    if 'violations_after_template' in result:
        print(f'Fixed template re-rendered and re-scanned: {result["violations_after_template"]} violation node(s) '
              f'({"verified" if result["template_verified"] else "NOT all fixes reached the template"}).')
    print(f'Wrote {out}')
    return EXIT_OK if not result['manual'] else EXIT_FINDINGS


def cmd_verify_evidence(args) -> int:
    from .accounts import verify_document
    try:
        doc = json.loads(Path(args.file).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        print(f'Cannot read {args.file}: {error}', file=sys.stderr)
        return EXIT_USAGE
    ok, message = verify_document(doc)
    print(('OK: ' if ok else 'NOT VALID: ') + message)
    return EXIT_OK if ok else EXIT_FINDINGS


def cmd_users(args) -> int:
    import getpass
    from . import accounts
    if args.users_command == 'list':
        for u in accounts.list_users():
            print(f'{u["user"]:<20} {u["role"]:<9} {u["display"]}  key {u["public_key"][:16]}…')
        if not accounts.list_users():
            print('No accounts yet. Accounts switch on as soon as the first one is added.')
        return EXIT_OK
    password = args.password or getpass.getpass(f'Password for {args.name} (10+ characters): ')
    try:
        u = accounts.create_user(args.name, args.display or args.name, password, args.role)
    except accounts.AccountError as error:
        print(error, file=sys.stderr)
        return EXIT_USAGE
    print(f'Created {u["user"]} ({u["role"]}). Accounts are now required in the app; decisions are signed with this key.')
    return EXIT_OK


def cmd_audit(args) -> int:
    ok, message, records = verify_ledger(Path(args.log))
    print(('OK: ' if ok else 'TAMPERING DETECTED: ') + message)
    if ok and records:
        print(f'Head hash: {records[-1]["hash"]}')
    return EXIT_OK if ok else EXIT_FINDINGS


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog='accessloop', description='Find, fix and verify accessibility problems in static HTML.')
    ap.add_argument('--version', action='version', version=f'AccessLoop {__version__}')
    sub = ap.add_subparsers(dest='command', required=True)

    s = sub.add_parser('scan', help='scan HTML files or folders')
    s.add_argument('paths', nargs='+')
    s.add_argument('--best-practice', action='store_true', default=True,
                   help='run axe best-practice rules too (default: on)')
    s.add_argument('--wcag-only', dest='best_practice', action='store_false',
                   help='run only the WCAG 2.x A/AA rules, without best-practice rules')
    s.add_argument('--extended', action='store_true',
                   help="add AccessLoop's browser checks: 320 px reflow, text spacing, keyboard focus, forced colours, open states")
    s.add_argument('--allow-scripts', action='store_true',
                   help='accept pages with scripts; the scripts are never run, so content built by JavaScript is not checked')
    s.add_argument('--assets-dir', help="folder to load the pages' own CSS/images/fonts from (default: each page's folder)")
    s.add_argument('--format', choices=['text', 'json', 'sarif', 'junit'], default='text')
    s.add_argument('--out', help='write the report to this file')
    s.add_argument('--fail-on', choices=['critical', 'serious', 'moderate', 'minor', 'any', 'none'], default='serious',
                   help='exit 1 when any violation is at or above this severity (default: serious)')
    s.add_argument('--quiet', action='store_true')
    s.set_defaults(func=cmd_scan)

    f = sub.add_parser('fix', help='propose fixes, apply the ones you approve, re-verify each one')
    f.add_argument('file')
    f.add_argument('--out', required=True, help='repaired copy (the original is never modified)')
    f.add_argument('--language', default='en', help='page language to use if the page has none (default: en)')
    f.add_argument('--best-practice', action='store_true', default=True, help='include best-practice rules (default: on)')
    f.add_argument('--wcag-only', dest='best_practice', action='store_false', help='only the WCAG 2.x A/AA rules')
    f.add_argument('--allow-scripts', action='store_true', help='accept pages with scripts (never run)')
    f.add_argument('--extended', action='store_true', help="include AccessLoop's browser checks")
    f.add_argument('--approve-auto', action='store_true',
                   help='unattended: apply only fixes that need no typed text; skip the rest (needs --reviewer)')
    f.add_argument('--agent', action='store_true',
                   help='agent mode: repair on its own within a policy, verify each change, list what needs a person (needs --reviewer)')
    f.add_argument('--risk', choices=['low', 'medium'], default='low', help='agent mode: highest risk it may apply (default: low)')
    f.add_argument('--max-changes', type=int, default=200, help='agent mode: most writes in one run (default: 200)')
    f.add_argument('--reviewer', help='name recorded with every decision')
    f.add_argument('--user', help='sign every decision with this account (asks for its password)')
    f.add_argument('--force-interactive', action='store_true', help=argparse.SUPPRESS)
    f.set_defaults(func=cmd_fix)

    a = sub.add_parser('audit', help='audit log tools')
    a_sub = a.add_subparsers(dest='audit_command', required=True)
    v = a_sub.add_parser('verify', help='check an audit log has not been edited')
    v.add_argument('log')
    v.set_defaults(func=cmd_audit)
    ve = a_sub.add_parser('verify-evidence', help='check the signature on a signed evidence file')
    ve.add_argument('file')
    ve.set_defaults(func=cmd_verify_evidence)

    t = sub.add_parser('template', help='fix a server-side template (Jinja, Thymeleaf, JSP, Handlebars, ...)')
    t.add_argument('template')
    t.add_argument('--out', required=True, help='fixed template (the original is never modified)')
    t.add_argument('--context', help='JSON file to render a Jinja template with (enables end-to-end verification)')
    t.add_argument('--rendered', help='a rendered sample page, for engines AccessLoop cannot render itself')
    t.add_argument('--reviewer', help='name recorded with every decision')
    t.add_argument('--wcag-only', action='store_true')
    t.set_defaults(func=cmd_template)

    i = sub.add_parser('issues', help='turn what is left on a page into tracker issues (Jira CSV or GitHub)')
    i.add_argument('file')
    i.add_argument('--jira', help='write a Jira import CSV to this file')
    i.add_argument('--github', metavar='OWNER/REPO', help='GitHub repository for the issues')
    i.add_argument('--create', action='store_true', help='actually file them with the GitHub CLI (gh)')
    i.add_argument('--wcag-only', action='store_true')
    i.add_argument('--allow-scripts', action='store_true')
    i.set_defaults(func=cmd_issues)

    u = sub.add_parser('users', help='manage local reviewer accounts (each gets a signing key)')
    u_sub = u.add_subparsers(dest='users_command', required=True)
    ua = u_sub.add_parser('add', help='add an account')
    ua.add_argument('name')
    ua.add_argument('--display', help='full name shown in reports')
    ua.add_argument('--role', choices=['reviewer', 'approver', 'admin'], default='reviewer')
    ua.add_argument('--password', help=argparse.SUPPRESS)
    ua.set_defaults(func=cmd_users)
    ul = u_sub.add_parser('list', help='list accounts')
    ul.set_defaults(func=cmd_users)
    return ap


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:
        return EXIT_USAGE if exit_.code not in (0, None) else EXIT_OK
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
