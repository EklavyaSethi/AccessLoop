"""Rejecting a fix: nothing is written, the card leaves the review list, the agent never applies it, and it can be
offered again."""
from pathlib import Path

import pytest
from accessloop import scanner

ROOT = Path(__file__).resolve().parent.parent
needs_axe = pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')


@needs_axe
def test_reject_removes_card_moves_to_queue_and_agent_respects_it():
    from accessloop.web.server import Session
    s = Session(ROOT)
    s.load(None, '', 'examples/samples/02_sip_signup.html')
    s.scan('en')
    st = s.state()
    auto = next(p for p in st['proposals'] if not p['needs_input'])
    sha = st['sha_current']
    s.reject(auto['id'], 'Yanis Singla')
    st = s.state()
    assert st['sha_current'] == sha                                            # nothing written
    assert not any(p['rule'] == auto['rule'] and p['selector'] == auto['selector'] for p in st['proposals'])
    queued = [u for u in st['unresolved'] if u.get('rejected')]
    assert queued and 'Yanis Singla' in queued[0]['handling_label']
    assert any(e['event'] == 'rejected' for e in st['events'])
    run = s.run_agent(['low', 'medium'], 50, 'Yanis Singla', 'en')
    st = s.state()
    assert any(u.get('rejected') and u['rule'] == auto['rule'] for u in st['unresolved'])   # agent left it alone
    assert 'rejected' in run['policy_text']
    s.unreject(auto['rule'], auto['selector'], 'Yanis Singla')
    assert any(p['rule'] == auto['rule'] and p['selector'] == auto['selector'] for p in s.state()['proposals'])
