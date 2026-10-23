import re
import pytest
from accessloop.workflow import Workflow, WorkflowError
from accessloop.planner import sha256
from accessloop.models import Finding, ScanResult
from conftest import fake_scanner


def test_complete_three_issue_loop(tmp_path, source):
    engine = Workflow(tmp_path, scanner=fake_scanner)
    engine.load(source)
    result = engine.scan()
    assert len(result.findings) == 3
    assert {p.rule_id for p in engine.proposals} == {'html-has-lang', 'label', 'button-name'}
    for _ in range(3):
        proposal = engine.proposals[0]
        outcome = engine.apply(proposal.proposal_id, approved=True)
        assert outcome.status == 'verified', outcome.detail
    assert len(engine.current_scan.findings) == 0
    assert sha256((tmp_path/'original.html').read_text()) == sha256(source)
    assert len(list((tmp_path/'backups').glob('*.html'))) == 3
    assert engine.report_json().count('verified') >= 3


def test_rejected_edits_do_not_write(tmp_path, source):
    engine = Workflow(tmp_path, scanner=fake_scanner)
    engine.load(source)
    engine.scan()
    original_hash = sha256(engine.current_html)
    outcome = engine.reject(engine.proposals[0].proposal_id)
    assert outcome.status == 'rejected'
    assert sha256(engine.current_html) == original_hash
    assert not (tmp_path/'backups').exists()


def test_no_approval_means_no_write(tmp_path, source):
    engine = Workflow(tmp_path, scanner=fake_scanner)
    engine.load(source)
    engine.scan()
    outcome = engine.apply(engine.proposals[0].proposal_id, approved=False)
    assert outcome.status == 'rejected'
    assert engine.current_html == source


def test_stale_proposal_blocked(tmp_path, source):
    engine = Workflow(tmp_path, scanner=fake_scanner)
    engine.load(source)
    engine.scan()
    stale = engine.proposals[-1]
    engine.apply(engine.proposals[0].proposal_id, approved=True)
    with pytest.raises(WorkflowError):
        engine.apply(stale.proposal_id, approved=True)


def test_regression_rolls_back_and_preserves_hash(tmp_path, source):
    def new_regression_after_patch(html):
        base = fake_scanner(html)
        if re.search(r'<html\b[^>]*\blang=', html, re.I):
            return ScanResult(base.findings + (Finding('color-contrast','#fake','serious','bad contrast','regression'),))
        return base
    engine = Workflow(tmp_path, scanner=new_regression_after_patch)
    engine.load(source)
    engine.scan()
    before = sha256(engine.current_html)
    result = engine.apply(engine.proposals[0].proposal_id, approved=True)
    assert result.status == 'rolled_back'
    assert sha256(engine.current_html) == before
    assert engine.events[-1]['event'] == 'rolled_back'


def test_browser_scan_failure_rolls_back(tmp_path, source):
    calls = 0
    def broken_scanner(html):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError('Browser unavailable')
        return fake_scanner(html)
    engine = Workflow(tmp_path, scanner=broken_scanner)
    engine.load(source)
    engine.scan()
    outcome = engine.apply(engine.proposals[0].proposal_id, approved=True)
    assert outcome.status == 'rolled_back'
    assert engine.current_html == source


def test_disallow_active_html(tmp_path, source):
    engine = Workflow(tmp_path, scanner=fake_scanner)
    with pytest.raises(WorkflowError):
        engine.load(source.replace('</body>', '<script>alert(1)</script></body>'))
    with pytest.raises(WorkflowError):
        engine.load(source.replace('<main>', '<main onclick="evil()">'))


def test_ambiguous_icon_not_auto_labeled(tmp_path):
    from pathlib import Path
    source = (Path(__file__).resolve().parent.parent / 'examples/ambiguous_icon_button.html').read_text()
    def ambiguous(_):
        return ScanResult((Finding('button-name','#icon-action','critical','Unnamed button','No clear label'),))
    engine = Workflow(tmp_path, scanner=ambiguous)
    engine.load(source)
    engine.scan()
    assert engine.current_scan.findings[0].rule_id == 'button-name'
    # The agent never invents a name: the only proposal asks the reviewer to type one.
    assert len(engine.proposals) == 1 and engine.proposals[0].needs_input and not engine.proposals[0].new_html
    before = engine.current_html
    with pytest.raises(WorkflowError):
        engine.apply(engine.proposals[0].proposal_id, approved=True)
    assert engine.current_html == before


def test_report_includes_counts_and_events(tmp_path, source):
    import json
    engine = Workflow(tmp_path, scanner=fake_scanner)
    engine.load(source)
    engine.scan()
    data = json.loads(engine.report_json())
    assert data['baseline_counts']['label'] == 1
    assert data['current_sha256'] == sha256(source)
    assert data['audit_events'][0]['event'] == 'loaded'


def test_crlf_preserved_in_backup_and_rejection(tmp_path, source):
    crlf = source.replace('\n', '\r\n')
    engine = Workflow(tmp_path, scanner=fake_scanner)
    engine.load(crlf)
    engine.scan()
    engine.reject(engine.proposals[0].proposal_id)
    assert engine.current_html == crlf
    assert (tmp_path / 'working.html').read_bytes() == crlf.encode()


def _scope_scanner(html, **kwargs):
    from accessloop.htmlsource import Doc
    from accessloop.models import Finding, ScanResult
    doc = Doc(html)
    return ScanResult(tuple(Finding('scope-attr-valid', 'td', 'moderate', 'h', 'd', uid=e.uid)
                            for e in doc.elements if e.tag == 'td' and e.get('scope') is not None))


def test_batch_applies_all_or_nothing(tmp_path):
    from accessloop.workflow import Workflow, WorkflowError
    page = ('<!doctype html><html lang="en"><head><title>t</title></head><body><main><table><tr>'
            '<td scope="row">a</td><td scope="col">b</td><td scope="row">c</td></tr></table></main></body></html>')
    e = Workflow(tmp_path, scanner=_scope_scanner)
    e.load(page)
    e.scan()
    ids = [p.proposal_id for p in e.proposals]
    assert len(ids) == 3
    out = e.apply_batch(ids, reviewer='Asha')
    assert out.status == 'verified' and 'scope=' not in e.current_html and not e.proposals
    assert e.events[-1]['batch'] == ids and e.audit_status()['verified']
    with pytest.raises(WorkflowError):
        e.apply_batch(ids[:1])


def test_batch_rolls_back_when_not_every_fix_works(tmp_path):
    from accessloop.workflow import Workflow
    from accessloop.models import Finding, ScanResult
    page = ('<!doctype html><html lang="en"><head><title>t</title></head><body><main><table><tr>'
            '<td scope="row">a</td><td scope="col">b</td></tr></table></main></body></html>')
    calls = {'n': 0}

    def stubborn(html, **kwargs):
        calls['n'] += 1
        res = _scope_scanner(html)
        if calls['n'] > 1:   # pretend one of the two problems is still there after the batch
            return ScanResult((Finding('scope-attr-valid', 'td', 'moderate', 'h', 'd', uid=None),))
        return res
    e = Workflow(tmp_path, scanner=stubborn)
    e.load(page)
    e.scan()
    out = e.apply_batch([p.proposal_id for p in e.proposals])
    assert out.status == 'rolled_back' and e.current_html == page and 'Only 1 of 2' in out.detail


def test_undo_one_earlier_fix_keeps_later_ones(tmp_path):
    from accessloop.workflow import Workflow
    page = ('<!doctype html><html lang="en"><head><title>t</title></head><body><main><table><tr>'
            '<td scope="row">a</td><td scope="col">b</td><td scope="row">c</td></tr></table></main></body></html>')
    e = Workflow(tmp_path, scanner=_scope_scanner)
    e.load(page)
    e.scan()
    for _ in range(3):
        e.apply(e.proposals[0].proposal_id, approved=True)
    assert 'scope=' not in e.current_html
    ops = e.changes()
    assert [o['status'] for o in ops] == ['active'] * 3
    out = e.revert(1, reviewer='Asha')                  # undo only the middle fix
    assert out.status == 'verified'
    assert e.current_html.count('scope=') == 1 and 'scope="col"' in e.current_html
    assert e.changes()[1]['status'] == 'reverted' and e.events[-1]['event'] == 'reverted'
    import pytest as _p
    from accessloop.workflow import WorkflowError
    with _p.raises(WorkflowError):
        e.revert(1)
