"""Streamlit pages. (1) Smoke test of every page with a stand-in streamlit; (2) real AppTest when Streamlit is installed."""
import importlib
import importlib.util
import sys
from pathlib import Path

import pytest
from accessloop import scanner
import fake_streamlit as fake

HAS_STREAMLIT = importlib.util.find_spec('streamlit') is not None  # evaluated before any stand-in is installed
ROOT = Path(__file__).resolve().parent.parent
needs_axe = pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')
PAGES = ['home', 'load', 'scan', 'agent', 'review', 'verify', 'manual', 'checklist', 'preview', 'site', 'reports', 'audit', 'trace', 'coverage', 'how']


def render(st, name):
    mod = importlib.import_module(f'streamlit_ui.views.{name}')
    try:
        mod.render()
    except fake.StopScript:
        pass
    return mod


def test_every_page_renders_before_anything_is_loaded():
    st = fake.install()
    st.session_state.clear()
    for name in PAGES:
        render(st, name)
    assert not st.errors


def test_nav_covers_every_view_and_builds():
    st = fake.install()
    from streamlit_ui import nav
    sections = nav.build()
    assert [k for _, k, *_ in nav.SPEC] == PAGES
    assert set(nav.PAGES) == set(PAGES)
    assert list(sections)[0] == '' and 'Workspace' in sections and 'Review' in sections and 'Evidence' in sections and 'Reference' in sections
    st.rendered.clear()
    nav.sidebar()     # our accessible replacement for Streamlit's menu: one plain link per page
    assert sum(1 for kind, *_ in st.rendered if kind == 'page_link') == len(nav.SPEC)


@needs_axe
def test_full_workflow_through_the_pages():
    st = fake.install(clicks={'load_sample'})
    st.session_state.clear()
    st.session_state['al_language'] = 'en-IN'
    render(st, 'load')  # clicking "Load sample" loads the first sample and reruns
    from streamlit_ui import ui
    s = ui.session()
    assert s.state()['loaded']

    st = fake.install(clicks=set())
    st.session_state['al_session'] = s
    s.load(None, '', 'examples/samples/02_sip_signup.html')
    st.session_state['al_language'] = 'en-IN'
    st.session_state['al_reviewer'] = 'Tester'
    for name in ('load', 'scan', 'manual', 'preview', 'audit', 'coverage', 'how'):
        render(st, name)

    # Scan
    st = fake.install(clicks={'run_scan'})
    st.session_state['al_session'] = s
    st.session_state['al_language'] = 'en-IN'
    render(st, 'scan')
    state = s.state()
    assert state['scanned'] and state['proposals']

    # Rendering Review without a click must not approve anything
    st = fake.install()
    st.session_state['al_session'] = s
    st.session_state['al_language'] = 'en-IN'
    render(st, 'review')
    assert s.state()['metrics']['verified'] == 0 and s.state()['outcome'] is None

    # Review, approve the first proposal
    pid = state['proposals'][0]['id']
    st = fake.install(clicks={'approve_' + pid})
    st.session_state['al_session'] = s
    st.session_state['al_language'] = 'en-IN'
    st.session_state['al_reviewer'] = 'Tester'
    render(st, 'review')
    out = s.state()['outcome']
    assert out['status'] == 'verified'

    # Every page renders in the scanned state with no errors
    st = fake.install()
    st.session_state['al_session'] = s
    for name in PAGES:
        render(st, name)
    assert not st.errors
    kinds = {k for k, *_ in st.rendered}
    assert 'download_button' in kinds and 'components.html' in kinds


@needs_axe
def test_page_text_is_escaped():
    from streamlit_ui import ui
    assert ui.badge('<script>', 'critical').count('<script>') == 0
    html = ui.diff_html([{'kind': 'add', 'text': '<img src=x onerror=alert(1)>'}])
    assert '<img' not in html and '&lt;img' in html


@pytest.mark.skipif(not HAS_STREAMLIT, reason='Streamlit is not installed')
def test_app_runs_under_streamlit_apptest():
    # Runs in a fresh interpreter state: remove the stand-in first.
    for name in [m for m in sys.modules if m == 'streamlit' or m.startswith('streamlit.') or m.startswith('streamlit_ui')]:
        del sys.modules[name]
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]


@needs_axe
def test_review_page_collects_typed_text_and_never_guesses():
    st = fake.install()
    st.session_state.clear()
    from streamlit_ui import ui
    s = ui.session()
    s.load(None, '', 'examples/samples/02_sip_signup.html')
    s.scan('en')
    alt = next(p for p in s.state()['proposals'] if p['rule'] == 'image-alt')

    # Approve with an empty text box: refused, nothing written.
    st = fake.install(clicks={'approve_' + alt['id']}, inputs={'Alternative text': ''})
    st.session_state['al_session'] = s
    st.session_state['al_language'] = 'en'
    st.session_state['al_reviewer'] = 'Tester'
    before = s.state()['sha_current']
    render(st, 'review')
    assert s.state()['sha_current'] == before and st.errors

    # Approve with the reviewer's own words: verified, and the words are in the audit log.
    st = fake.install(clicks={'approve_' + alt['id']}, inputs={'Alternative text': 'SIP growth chart'})
    st.session_state['al_session'] = s
    st.session_state['al_language'] = 'en'
    st.session_state['al_reviewer'] = 'Tester'
    render(st, 'review')
    state = s.state()
    assert state['outcome']['status'] == 'verified' and 'SIP growth chart' in state['fix_log'][-1]['after']


def test_hindi_interface_translates_workflow_screens_and_marks_language():
    st = fake.install()
    st.session_state.clear()
    st.session_state['al_ui_lang'] = 'hi'
    from streamlit_ui import i18n, nav
    for name in PAGES:
        render(st, name)
    assert not st.errors
    html = ' '.join(str(a[0]) for kind, a, _ in st.rendered if kind == 'markdown' and a)
    assert 'lang="hi"' in html and 'पेज लोड करें' in html and 'सुधार प्रस्तावों की समीक्षा' in html
    buttons = [a[0] for kind, a, _ in st.rendered if kind == 'button']
    assert 'नमूना पेज लोड करें' in buttons
    titles = [p.kwargs['title'] for sec in nav.build().values() for p in sec]
    assert '2 · स्कैन' in titles
    # every workflow page title has a Hindi version; engine findings are left in English on purpose
    for title in ('Load a page', 'Scan the page', 'Review repair proposals', 'Verify results', 'Reports and downloads'):
        assert title in i18n.PAGES_HI
    st.session_state['al_ui_lang'] = 'en'
    assert i18n.t('Verified') == 'Verified'


@needs_axe
def test_agent_page_runs_the_agent_and_shows_questions():
    st = fake.install()
    st.session_state.clear()
    from streamlit_ui import ui
    s = ui.session()
    s.load(None, '', 'examples/samples/08_legacy_portal_gallery.html')
    st = fake.install(clicks={'agent_go'})
    st.session_state['al_session'] = s
    render(st, 'agent')
    assert not s.state().get('agent'), 'the agent must not run without a name on record'
    st = fake.install(clicks={'agent_go'})
    st.session_state['al_session'] = s
    st.session_state['al_reviewer'] = 'Yanis Singla'
    render(st, 'agent')
    run = s.state()['agent']
    assert run and run['applied'] > 0
    st = fake.install()
    st.session_state['al_session'] = s
    render(st, 'agent')
    assert not st.errors
    text = ' '.join(str(a[0]) for kind, a, _ in st.rendered if kind in ('markdown', 'subheader') and a)
    assert 'What happened' in text and 'needs your words' in text and 'al-tl' in text
    assert 'role="log"' in text and 'audit entry' in text     # the agent console shows the real run


def test_ai_panel_shows_status_and_never_leaks_the_key():
    import os
    st = fake.install()
    st.session_state.clear()
    from streamlit_ui import ui
    old = {k: os.environ.get(k) for k in ('ACCESSLOOP_AI', 'GEMINI_API_KEY')}
    try:
        os.environ['ACCESSLOOP_AI'] = 'off'
        assert 'AI off' in ui.ai_status_html()
        ui.ai_panel()
        os.environ['ACCESSLOOP_AI'] = 'gemini'
        os.environ['GEMINI_API_KEY'] = 'SECRET-test-key-123'
        assert 'not tested yet' in ui.ai_status_html()
        st.session_state['al_ai_probe'] = {'ok': True, 'provider': 'gemini', 'checked_at': '10:20:00', 'seconds': 3.1,
                                           'sample': 'Rates chart'}
        html = ui.ai_status_html()
        assert 'connected' in html and 'Google Gemini' in html
        st.rendered.clear()
        ui.ai_panel()
        shown = ' '.join(str(a) + str(k) for _, a, k in st.rendered)
        assert 'SECRET-test-key-123' not in shown and 'SECRET' not in html
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@needs_axe
def test_review_page_shows_where_each_fix_is():
    st = fake.install()
    st.session_state.clear()
    from streamlit_ui import ui
    s = ui.session()
    s.load(None, '', 'examples/samples/02_sip_signup.html')
    s.scan('en')
    pid = s.state()['proposals'][0]['id']
    st = fake.install(clicks={f'pic_{pid}'})
    st.session_state['al_session'] = s
    st.session_state['al_reviewer'] = 'Yanis Singla'
    render(st, 'review')
    assert not st.errors
    html = ' '.join(str(a[0]) for kind, a, _ in st.rendered if kind == 'markdown' and a)
    assert 'Where:' in html and 'al-code' in html and '▶' in html
    kinds = [kind for kind, *_ in st.rendered]
    assert 'image' in kinds or any('nothing to picture' in str(a) or 'page setting' in str(a) for _, a, _ in st.rendered)
