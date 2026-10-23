import json
import tempfile
from pathlib import Path

from accessloop.ledger import Ledger, verify
from accessloop.models import Finding, ScanResult
from accessloop.workflow import Workflow


def _log(tmp: Path) -> Path:
    path = tmp / 'audit.jsonl'
    led = Ledger(path)
    for i in range(4):
        led.append('event', f'entry {i}', value=i)
    return path


def test_chain_verifies_and_survives_reopen():
    path = _log(Path(tempfile.mkdtemp()))
    ok, message, records = verify(path)
    assert ok and len(records) == 4
    again = Ledger(path)
    again.append('more', 'appended after reopening')
    assert verify(path)[0] and len(verify(path)[2]) == 5


def test_edit_delete_reorder_and_insert_are_detected():
    base = Path(tempfile.mkdtemp())
    for kind in ('edit', 'delete', 'swap', 'insert', 'truncate-hash'):
        path = _log(base / kind)
        lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
        if kind == 'edit':
            rec = json.loads(lines[1]); rec['detail'] = 'changed'; lines[1] = json.dumps(rec, sort_keys=True) + '\n'
        elif kind == 'delete':
            del lines[2]
        elif kind == 'swap':
            lines[1], lines[2] = lines[2], lines[1]
        elif kind == 'insert':
            lines.insert(1, lines[0])
        else:
            rec = json.loads(lines[3]); rec['hash'] = '0' * 64; lines[3] = json.dumps(rec, sort_keys=True) + '\n'
        path.write_text(''.join(lines), encoding='utf-8')
        ok, message, _ = verify(path)
        assert not ok, kind


def _fake(findings):
    return lambda html, **k: ScanResult(tuple(findings))


def test_reset_is_recorded_not_erased():
    page = '<!doctype html><html><head><title>t</title></head><body><main><p>x</p></main></body></html>'
    finding = Finding('html-has-lang', 'html', 'serious', 'h', 'd', uid=0)
    tmp = Path(tempfile.mkdtemp())
    calls = {'n': 0}

    def scanner(html, **k):
        calls['n'] += 1
        return ScanResult(() if 'lang=' in html else (finding,))
    e = Workflow(tmp, scanner=scanner)
    e.load(page)
    e.scan()
    out = e.apply(e.proposals[0].proposal_id, approved=True, reviewer='Asha')
    assert out.status == 'verified'
    e.reset()
    kinds = [r['event'] for r in e.events]
    assert kinds == ['loaded', 'scanned', 'verified', 'reset']
    assert e.events[2]['reviewer'] == 'Asha' and e.events[2]['rule'] == 'html-has-lang'
    assert e.run_events[0]['event'] == 'reset' and e.audit_status()['verified']
    assert e.current_html == page
