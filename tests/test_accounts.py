import json
import tempfile
from pathlib import Path

import pytest
from accessloop import accounts
from accessloop.ledger import verify
from accessloop.web.server import ApiError, Session

ROOT = Path(__file__).resolve().parent.parent


def _fresh_home() -> Path:
    """A new, empty accounts folder for this test (set through the environment, like a real install)."""
    import os
    d = tempfile.mkdtemp()
    os.environ['ACCESSLOOP_HOME'] = d
    return Path(d)


def test_accounts_login_and_signatures():
    home = _fresh_home()
    assert not accounts.enabled()
    accounts.create_user('asha', 'Asha Rao', 'correct horse 1', 'reviewer')
    accounts.create_user('vik', 'Vikram S', 'battery staple 2', 'approver')
    assert accounts.enabled()
    with pytest.raises(accounts.AccountError):
        accounts.login('asha', 'wrong password!')
    with pytest.raises(accounts.AccountError):
        accounts.create_user('asha', 'dup', 'whatever123', 'reviewer')
    me = accounts.login('asha', 'correct horse 1')
    doc = accounts.sign_document({'a': 1, 'b': [1, 2]}, me)
    ok, msg = accounts.verify_document(doc)
    assert ok and 'asha' in msg
    doc['a'] = 2
    assert not accounts.verify_document(doc)[0]
    raw = json.loads((home / 'users.json').read_text())
    assert 'correct horse' not in json.dumps(raw) and raw['users']['asha']['private_key_enc']
    _fresh_home()   # leave accounts switched off for the tests that follow


def test_session_requires_sign_in_and_four_eyes():
    _fresh_home()
    accounts.create_user('asha', 'Asha Rao', 'correct horse 1', 'reviewer')
    accounts.create_user('vik', 'Vikram S', 'battery staple 2', 'approver')
    s = Session(ROOT)
    with pytest.raises(ApiError):
        s.load(None, '', 'examples/samples/04_insurance_claim.html')
    s.login('asha', 'correct horse 1')
    s.load(None, '', 'examples/samples/04_insurance_claim.html')
    s.scan('en')
    s.set_four_eyes(True)
    pid = s.state()['proposals'][0]['id']
    s.approve(pid, 'en', 'ignored typed name')
    st = s.state()
    assert st['outcome']['status'] == 'pending' and st['metrics']['verified'] == 0 and st['auth']['pending']
    with pytest.raises(ApiError):          # same person cannot confirm
        s.confirm(pid, '')
    s.logout()
    s.login('vik', 'battery staple 2')
    s.confirm(pid, '')
    st = s.state()
    assert st['outcome']['status'] == 'verified' and 'Asha Rao' in st['fix_log'][-1]['reviewer'] and 'Vikram' in st['fix_log'][-1]['reviewer']
    ok, message, records = verify(s.engine.workspace / 'audit.jsonl')
    assert ok and 'signed by reviewers' in message
    signers = {r['signer']['user'] for r in records if r.get('signer')}
    assert {'asha', 'vik'} <= signers
    content, name, _ = s.export('evidence')
    assert accounts.verify_document(json.loads(content))[0] and name.endswith('_signed.json')
    _fresh_home()


def test_tampered_signature_is_detected():
    _fresh_home()
    accounts.create_user('asha', 'Asha Rao', 'correct horse 1', 'reviewer')
    s = Session(ROOT)
    s.login('asha', 'correct horse 1')
    s.load(None, '', 'examples/samples/04_insurance_claim.html')
    s.record_manual('2.4.7', 'pass', 'ok', '')
    log = s.engine.workspace / 'audit.jsonl'
    lines = log.read_text().splitlines()
    rec = json.loads(lines[-1])
    rec['result'] = 'fail'
    from accessloop.ledger import record_hash
    rec['hash'] = record_hash(rec)          # even with a recomputed hash, the signature no longer matches
    lines[-1] = json.dumps(rec, sort_keys=True)
    log.write_text('\n'.join(lines) + '\n')
    ok, message, _ = verify(log)
    _fresh_home()
    assert not ok and 'signature' in message
