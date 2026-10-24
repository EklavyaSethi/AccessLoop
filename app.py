"""AccessLoop Streamlit app (multi-page). Launch:  streamlit run app.py

Pages live in streamlit_ui/views. All logic is in accessloop.web.server.Session (also used by the local web UI and tested).
"""
from __future__ import annotations
from html import escape

import streamlit as st

from streamlit_ui import nav, theme, ui

st.set_page_config(page_title='AccessLoop · Reviewed accessibility repair', page_icon='♿', layout='wide',
                   initial_sidebar_state='expanded')
ui.setup()
try:
    st.logo(str(theme.LOGO_PATH))
except Exception:  # noqa: BLE001 - the logo is cosmetic
    pass

session = ui.session()
if session.auth_required():
    # Accounts are switched on (users.json has at least one account): nothing works until someone signs in.
    st.markdown('<div class="al-head"><div class="eyebrow">AccessLoop</div><h1>Sign in</h1>'
                '<p>Every decision you make is signed with your personal key and recorded in the audit log.</p></div>',
                unsafe_allow_html=True)
    with st.form('login'):
        user = st.text_input('User name', autocomplete='username')
        password = st.text_input('Password', type='password', autocomplete='current-password')
        if st.form_submit_button('Sign in', type='primary'):
            if ui.run(session.login, user, password):
                st.rerun()
    st.stop()

from streamlit_ui.i18n import LANGS
with st.sidebar:
    if not ((ui.session().state().get('auth') or {}).get('user')):
        st.text_input('Your name (required)', key='al_reviewer', max_chars=80, placeholder='e.g. Yanis Singla',
                      help='Recorded with every decision and agent run, in the audit log and the evidence report. '
                           'For verified, signed identities add accounts: python -m accessloop users add NAME.')
    ui.ai_panel()
    st.selectbox('Interface language / इंटरफ़ेस की भाषा', list(LANGS), format_func=LANGS.get, key='al_ui_lang',
                 help='Hindi covers navigation, page introductions, steps, buttons and key labels. Findings stay in English.')
try:
    page = st.navigation(nav.build(), position='hidden')   # replaced by nav.sidebar(): accessible plain links
    with st.sidebar:
        nav.sidebar()
except TypeError:   # Streamlit older than 1.36 has no position argument
    page = st.navigation(nav.build())

with st.sidebar:
    state = ui.session().state()
    if state['loaded']:
        rows = f'<div class="row"><span>File</span><span>{escape(state["source_name"])}</span></div>'
        if state['scanned']:
            m = state['metrics']
            rows += (f'<div class="row"><span>Violations</span><span>{m["baseline"]} → {m["current"]}</span></div>'
                     f'<div class="row"><span>Verified fixes</span><span>{m["verified"]}</span></div>')
        else:
            rows += '<div class="row"><span>Status</span><span>Not scanned</span></div>'
        st.markdown(f'<div class="al-side"><b>Current session</b>{rows}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="al-side"><b>Current session</b>No page loaded yet.</div>', unsafe_allow_html=True)
    auth = state.get('auth') or {}
    if auth.get('user'):
        u = auth['user']
        st.caption(f'Signed in as {u["display"]} ({u["role"]}). Your decisions are signed.')
        if st.button(ui.t('Sign out'), key='logout'):
            session.logout()
            st.rerun()
    st.caption(ui.t('Runs locally. Page code never leaves this machine.'))

page.run()
