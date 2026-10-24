"""AI-drafted answers and the agent run report. The model is replaced by a stand-in: no network in tests."""
import json
import os
import tempfile
from pathlib import Path

import pytest
from accessloop import agent, agent_report, ai_drafts, scanner
from accessloop.workflow import Workflow, read_source

ROOT = Path(__file__).resolve().parent.parent
needs_axe = pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')


class _Env:
    def __init__(self, **kv):
        self.kv, self.old = kv, {}

    def __enter__(self):
        for k, v in self.kv.items():
            self.old[k] = os.environ.get(k)
            os.environ[k] = v

    def __exit__(self, *a):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _after_agent(name='08_legacy_portal_gallery'):
    e = Workflow(Path(tempfile.mkdtemp()))
    e.load(read_source(ROOT / 'examples' / 'samples' / f'{name}.html'))
    agent.run(e)
    return e


def test_words_from_names():
    assert ai_drafts._words('banner-sip.png') == 'Banner sip'
    assert ai_drafts._words('#risk') == 'Risk' and ai_drafts._words('fullName') == 'Full name'
    assert ai_drafts._words('img_0042.jpg') == ''          # generic file names give no suggestion


def test_validation_rejects_markup_wrong_options_and_long_text():
    text = {'kind': 'text', 'max': 20}
    assert ai_drafts._valid('  Mobile   number ', text) == 'Mobile number'
    assert ai_drafts._valid('<b>x</b>', text) is None and ai_drafts._valid('see https://x.y', text) is None
    assert len(ai_drafts._valid('a' * 50, text)) == 20
    sel = {'kind': 'select', 'options': [('en', 'English'), ('hi', 'Hindi')]}
    assert ai_drafts._valid('hi', sel) == 'hi' and ai_drafts._valid('fr', sel) is None


@needs_axe
def test_rule_based_when_ai_is_off_and_nothing_applied():
    e = _after_agent()
    before = e.current_html
    with _Env(ACCESSLOOP_AI='off'):
        lines = []
        out = ai_drafts.draft(e, e.proposals, consent=True, on_log=lambda ph, t: lines.append(t))
    assert out and all(d['_source'] == 'rules' and 'no AI' in d['_why'] for d in out.values())
    assert e.current_html == before                                        # drafting never writes
    assert e.events[-1]['event'] == 'ai_drafted' and e.events[-1]['provider'] == 'rules'
    assert 'switched off' in lines[0]


@needs_axe
def test_ai_drafts_are_validated_and_logged():
    e = _after_agent()
    todo = ai_drafts.eligible(e.proposals)
    good, bad_markup = todo[0], todo[1]
    sent = {}

    def fake(prompt):
        sent['prompt'] = prompt
        return {'drafts': [
            {'id': good.proposal_id, 'field': ai_drafts._fields(good)[0]['name'], 'value': 'Interest rates for fixed deposits',
             'confidence': 'medium', 'why': 'Image sits above the rates table.'},
            {'id': bad_markup.proposal_id, 'field': ai_drafts._fields(bad_markup)[0]['name'], 'value': '<img onerror=x>',
             'confidence': 'high', 'why': 'x'},
            {'id': 'not-a-proposal', 'field': 'alt', 'value': 'x', 'confidence': 'high', 'why': 'x'}]}
    real = ai_drafts._ask
    ai_drafts._ask = fake
    try:
        with _Env(ACCESSLOOP_AI='gemini'):
            out = ai_drafts.draft(e, e.proposals, consent=True)
    finally:
        ai_drafts._ask = real
    assert out[good.proposal_id]['_source'] == 'ai' and out[good.proposal_id]['_confidence'] == 'medium'
    assert out.get(bad_markup.proposal_id, {}).get('_source') != 'ai'      # dropped; at most a rule-based suggestion
    assert 'UNTRUSTED PAGE DATA' in sent['prompt'] and '@' not in sent['prompt'].split('Items:')[1].replace('"@', '')
    ev = e.events[-1]
    assert ev['event'] == 'ai_drafted' and ev['provider'] == 'gemini' and ev['consent'] is True


@needs_axe
def test_no_consent_means_no_ai_call_and_failure_falls_back():
    e = _after_agent()

    def boom(prompt):
        raise AssertionError('must not be called without consent')
    real = ai_drafts._ask
    ai_drafts._ask = boom
    try:
        with _Env(ACCESSLOOP_AI='gemini'):
            out = ai_drafts.draft(e, e.proposals, consent=False)
            assert all(d['_source'] == 'rules' for d in out.values())

            def down(prompt):
                raise ConnectionError('venue wifi is down')
            ai_drafts._ask = down
            out = ai_drafts.draft(e, e.proposals, consent=True)
    finally:
        ai_drafts._ask = real
    assert out and all(d['_source'] == 'rules' for d in out.values())
    assert 'venue wifi' in e.events[-1]['fallback_reason']


@needs_axe
def test_session_flow_records_how_a_draft_was_used_and_report_has_everything():
    from accessloop.web.server import Session
    s = Session(ROOT)
    s.load(None, '', 'examples/samples/08_legacy_portal_gallery.html')
    run = s.run_agent(['low'], 50, 'Yanis Singla', 'en', ai_drafts=True)
    st = s.state()
    assert run['drafts'] and st['ai_drafts'] and any(ph == 'ai' for _, ph, _ in run['console'])
    key, d = next((k, v) for k, v in st['ai_drafts'].items() if k.startswith('image-alt'))
    rule, selector, line = key.split('|')
    values = {k: v for k, v in d.items() if not k.startswith('_')}
    res = s.answer([{'rule': rule, 'selector': selector, 'line': int(line), 'values': values}], 'en', 'Yanis Singla')
    assert res[0]['status'] in ('verified', 'rolled_back')
    st = s.state()
    decision = next(ev for ev in st['events'] if ev['event'] == 'ai_draft_decision')
    assert decision['use'] == 'accepted as drafted' and decision['reviewer'] == 'Yanis Singla'
    assert any('rule-based suggestion, accepted as drafted' in f['decision'] for f in st['fix_log'])
    # agent run report
    html, name, mime = s.export('agent-html')
    raw, jname, _ = s.export('agent-json')
    doc = json.loads(raw)
    assert name.endswith('_agent_run_report.html') and 'Yanis Singla' in html and 'audit entry' in html
    assert doc['approved_by'] == 'Yanis Singla' and doc['summary']['applied'] > 0 and doc['changes']
    assert all(c['before'] and c['after'] for c in doc['changes'] if c['decision'] == 'approved by agent policy')
    events = [r['event'] for r in doc['audit']['run_entries']]
    assert events[0] == 'agent_started' and 'agent_finished' in events and 'ai_drafted' in events
    assert doc['audit']['verified'] is True


def test_report_needs_a_run():
    with pytest.raises(ValueError):
        agent_report.build({'events': []})


def test_follows_googles_named_replacement_for_a_retired_model():
    err = RuntimeError("ClientError: 404 NOT_FOUND. {'message': 'This model models/gemini-2.5-flash is no longer available "
                       "to new users. Please update your code to use models/gemini-3.8-flash for the latest features'}")
    assert ai_drafts._replacement(err) == 'gemini-3.8-flash'
    assert ai_drafts._replacement(RuntimeError('500 internal')) is None
    with _Env(ACCESSLOOP_AI='gemini'):
        os.environ.pop('GEMINI_MODEL', None)
        assert ai_drafts.model_name() == 'gemini-3.8-flash'


def test_busy_model_is_retried_then_falls_back_to_the_named_fallback():
    calls = []

    class Models:
        def generate_content(self, model, contents, config):
            calls.append(model)
            if model == 'gemini-3.8-flash':
                raise RuntimeError("ServerError: 503 UNAVAILABLE. This model is currently experiencing high demand.")
            return type('R', (), {'text': '{"drafts": []}'})()
    client = type('C', (), {'models': Models()})()
    with _Env(ACCESSLOOP_AI='gemini', GEMINI_MODEL='gemini-3.8-flash', GEMINI_FALLBACK_MODEL='backup-model'):
        r = ai_drafts.gemini_generate(client, 'x', None, waits=(0, 0))
    assert r.text == '{"drafts": []}' and calls == ['gemini-3.8-flash'] * 3 + ['backup-model']
    os.environ.pop('GEMINI_FALLBACK_MODEL', None)


def test_retired_model_switches_to_the_named_replacement():
    calls = []

    class Models:
        def generate_content(self, model, contents, config):
            calls.append(model)
            if model == 'old-model':
                raise RuntimeError("404 NOT_FOUND. Please update your code to use models/new-model for the latest")
            return type('R', (), {'text': '{}'})()
    client = type('C', (), {'models': Models()})()
    with _Env(ACCESSLOOP_AI='gemini', GEMINI_MODEL='old-model'):
        ai_drafts.gemini_generate(client, 'x', None, waits=(0, 0))
        assert calls == ['old-model', 'new-model']


@needs_axe
def test_slow_ai_never_blocks_the_rest_of_the_app():
    import threading
    import time as _t
    from accessloop.web.server import Session
    s = Session(ROOT)
    s.load(None, '', 'examples/samples/02_sip_signup.html')
    real = ai_drafts._ask

    def slow(prompt):
        _t.sleep(4)
        return {'drafts': []}
    ai_drafts._ask = slow
    try:
        with _Env(ACCESSLOOP_AI='gemini'):
            th = threading.Thread(target=lambda: s.run_agent(['low'], 50, 'Yanis Singla', 'en', ai_drafts=True, ai_consent=True))
            th.start()
            _t.sleep(2.5)                       # the agent has finished its fixes and is waiting on the model
            t0 = _t.perf_counter()
            state = s.state()                   # any page of the app reads this
            assert _t.perf_counter() - t0 < 1.0 and state['agent']['applied'] > 0
            th.join()
    finally:
        ai_drafts._ask = real


def test_ai_has_a_time_budget():
    calls = []

    class Models:
        def generate_content(self, model, contents, config):
            calls.append(model)
            raise RuntimeError('503 UNAVAILABLE high demand')
    client = type('C', (), {'models': Models()})()
    import time as _t
    t0 = _t.perf_counter()
    with pytest.raises(RuntimeError):
        ai_drafts.gemini_generate(client, 'x', None, waits=(1.0, 1.0), budget=3.0)
    assert _t.perf_counter() - t0 < 3.5
