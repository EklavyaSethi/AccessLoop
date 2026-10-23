import json
import tempfile
from pathlib import Path

import pytest
from accessloop import cli, scanner
from accessloop.ledger import Ledger
from accessloop.models import Finding, ScanResult

ROOT = Path(__file__).resolve().parent.parent
PAGE = '<!doctype html>\n<html>\n<head><title>t</title></head>\n<body><main><p>x</p></main></body>\n</html>\n'


def _fake(html, **kwargs):
    return ScanResult((Finding('html-has-lang', 'html', 'serious', 'Page must have a lang', 'd', uid=0),),
                      reviews=(Finding('bypass', 'html', 'serious', 'Bypass blocks', 'd', uid=0, kind='review'),))


def test_scan_file_reports_lines_fixes_and_kinds():
    path = Path(tempfile.mkdtemp()) / 'p.html'
    path.write_text(PAGE, encoding='utf-8')
    r = cli.scan_file(path, False, scanner=_fake)
    assert r['status'] == 'scanned' and r['violations'] == 1 and r['needs_review'] == 1
    lang = r['findings'][0]
    assert lang['line'] == 2 and lang['fix'] == 'automatic' and lang['kind'] == 'violation'


def test_refused_page_is_reported_not_scanned():
    path = Path(tempfile.mkdtemp()) / 'bad.html'
    path.write_text(PAGE.replace('<p>x</p>', '<script>x()</script>'), encoding='utf-8')
    assert cli.scan_file(path, False, scanner=_fake)['status'] == 'refused'


def test_sarif_shape():
    path = Path(tempfile.mkdtemp()) / 'p.html'
    path.write_text(PAGE, encoding='utf-8')
    sarif = cli.to_sarif([cli.scan_file(path, False, scanner=_fake)], {})
    assert sarif['version'] == '2.1.0'
    run = sarif['runs'][0]
    ids = [r['id'] for r in run['tool']['driver']['rules']]
    assert ids == ['bypass', 'html-has-lang']
    levels = {r['ruleId']: r['level'] for r in run['results']}
    assert levels == {'html-has-lang': 'error', 'bypass': 'note'}
    for res in run['results']:
        assert run['tool']['driver']['rules'][res['ruleIndex']]['id'] == res['ruleId']
        assert res['locations'][0]['physicalLocation']['region']['startLine'] == 2


def test_threshold_logic():
    assert cli._at_or_above('critical', 'serious') and cli._at_or_above('serious', 'serious')
    assert not cli._at_or_above('moderate', 'serious') and not cli._at_or_above('critical', 'none')


def test_usage_errors_and_audit_verify():
    assert cli.main(['scan', '/definitely/not/here']) == cli.EXIT_USAGE
    assert cli.main(['nonsense']) == cli.EXIT_USAGE
    tmp = Path(tempfile.mkdtemp())
    page = tmp / 'p.html'
    page.write_text(PAGE, encoding='utf-8')
    assert cli.main(['fix', str(page), '--out', str(page)]) == cli.EXIT_USAGE          # never overwrite the original
    assert cli.main(['fix', str(page), '--out', str(tmp / 'o.html'), '--approve-auto']) == cli.EXIT_USAGE  # needs reviewer
    log = tmp / 'a.jsonl'
    Ledger(log).append('loaded', 'x')
    assert cli.main(['audit', 'verify', str(log)]) == cli.EXIT_OK
    log.write_text(log.read_text().replace('loaded', 'scanned'), encoding='utf-8')
    assert cli.main(['audit', 'verify', str(log)]) == cli.EXIT_FINDINGS


@pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')
def test_real_scan_and_unattended_fix():
    sample = ROOT / 'examples/samples/04_insurance_claim.html'
    out = Path(tempfile.mkdtemp())
    assert cli.main(['scan', str(sample), '--format', 'json', '--out', str(out / 'r.json'), '--quiet']) == cli.EXIT_FINDINGS
    assert json.loads((out / 'r.json').read_text())['results'][0]['violations'] == 5
    code = cli.main(['fix', str(sample), '--out', str(out / 'fixed.html'), '--approve-auto', '--reviewer', 'CI'])
    assert code == cli.EXIT_OK and (out / 'fixed.audit.jsonl').is_file()
    assert cli.main(['audit', 'verify', str(out / 'fixed.audit.jsonl')]) == cli.EXIT_OK
    assert cli.main(['scan', str(out / 'fixed.html'), '--quiet']) == cli.EXIT_OK
