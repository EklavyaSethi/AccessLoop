"""Agent mode: acts only inside its policy, verifies every change, never types text, hands the rest to a person."""
import tempfile
from pathlib import Path

import pytest
from accessloop import agent, scanner
from accessloop.workflow import Workflow, WorkflowError, read_source
from accessloop.ledger import verify as verify_ledger

ROOT = Path(__file__).resolve().parent.parent
needs_axe = pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')


def _engine(name='08_legacy_portal_gallery'):
    e = Workflow(Path(tempfile.mkdtemp()))
    e.load(read_source(ROOT / 'examples' / 'samples' / f'{name}.html'))
    e.scan(best_practice=True)
    return e


def test_policy_gate():
    p = agent.Policy()
    mk = lambda **k: type('P', (), {'needs_input': False, 'rule_id': 'x', 'risk': 'low', 'selector': 's', 'before': 'b', **k})()  # noqa: E731
    assert p.allows(mk())[0]
    assert not p.allows(mk(needs_input=True))[0]
    assert not p.allows(mk(risk='medium'))[0]
    assert not agent.Policy(deny_rules=('x',)).allows(mk())[0]
    assert 'never types text' in p.describe()


def test_agent_refuses_without_a_page():
    with pytest.raises(WorkflowError):
        agent.run(Workflow(Path(tempfile.mkdtemp())))


@needs_axe
def test_agent_repairs_within_policy_and_hands_over_the_rest():
    e = _engine()
    original = (e.workspace / 'original.html').read_text(encoding='utf-8')
    seen = []
    r = agent.run(e, on_step=lambda s, run: seen.append(s.phase))
    assert r.applied > 0 and r.after < r.before
    assert seen[0] == 'perceive' and seen[-1] == 'stop' and 'commit' in seen
    phases = [ph for _, ph, _ in r.console]
    assert phases[0] == 'policy' and {'perceive', 'plan', 'gate', 'act', 'verify', 'commit', 'stop'} <= set(phases)
    assert any('audit entry' in text for _, ph, text in r.console if ph == 'commit')
    assert all(r.console[i][0] <= r.console[i + 1][0] for i in range(len(r.console) - 1))
    # nothing outside the policy was applied: every remaining proposal is either text or held
    assert all(p.needs_input or p.risk != 'low' for p in e.proposals)
    assert r.questions and all(q['fields'] for q in r.questions)
    assert (e.workspace / 'original.html').read_text(encoding='utf-8') == original
    ok, _, records = verify_ledger(e.workspace / 'audit.jsonl')
    assert ok and records[-1]['event'] == 'agent_finished' and any(x['event'] == 'agent_started' for x in records)
    # a wider policy does more, still never typing text
    r2 = agent.run(e, agent.Policy(risks=('low', 'medium')))
    assert r2.applied > 0 and not r2.held and r2.after <= r.after
    assert all(p.needs_input for p in e.proposals)


@needs_axe
def test_presentation_pace_is_left_out_of_reported_times():
    e = _engine('02_sip_signup')
    import time as _t
    t0 = _t.perf_counter()
    r = agent.run(e, pace=0.2)
    wall = _t.perf_counter() - t0
    assert wall - r.seconds >= 0.2 * (len(r.steps) - r.decisions) - 0.05     # pauses happened ...
    assert r.console[-1][0] <= r.seconds + 0.01                                # ... but are not counted as work


@needs_axe
def test_change_limit_and_deny_list():
    e = _engine()
    r = agent.run(e, agent.Policy(max_changes=1))
    assert r.decisions == 1 and 'limit' in r.stopped
    e = _engine()
    first = next(p.rule_id for p in e.proposals if not p.needs_input and p.risk == 'low')
    r = agent.run(e, agent.Policy(deny_rules=(first,)))
    assert all(s.rule != first for s in r.steps if s.phase == 'commit')


@needs_axe
def test_session_agent_and_answers_and_four_eyes():
    from accessloop.web.server import Session, ApiError
    s = Session(ROOT)
    s.load(None, '', 'examples/samples/02_sip_signup.html')
    run = s.run_agent(['low'], 50, 'Tester', 'en')
    st = s.state()
    agent_log = [f for f in st['fix_log'] if f['decision'] == 'approved by agent policy']
    assert agent_log and all(f['before'] and f['after'] and f['before'] != f['after'] for f in agent_log)
    assert st['agent']['applied'] > 0 and st['metrics']['current'] < st['metrics']['baseline']
    q = next(q for q in run['questions'] if any(f.get('kind', 'text') == 'text' for f in q['fields']))
    field = next(f for f in q['fields'] if f.get('kind', 'text') == 'text')
    res = s.answer([{'rule': q['rule'], 'selector': q['selector'], 'line': q['line'], 'values': {field['name']: 'Mobile number'}}],
                   'en', 'Tester')
    assert res and res[0]['status'] in ('verified', 'rolled_back')
    s.set_four_eyes(True)
    with pytest.raises(ApiError):
        s.run_agent(['low'], 50, 'Tester', 'en')
