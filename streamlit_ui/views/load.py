from __future__ import annotations
import streamlit as st
from .. import ui


def _languages(state: dict):
    return [(x['code'], x['name']) for x in state['languages']]


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Load a page', 'Choose a sample, upload an HTML file, or paste markup. HTML files under 2 MB are accepted, and your original is always kept untouched.', 1, state)
    ui.show_flash()

    with st.container(border=True):
        ui.h2(ui.t('Reviewer settings'))
        c1, c2 = st.columns(2)
        langs = _languages(state)
        codes = [c for c, _ in langs]
        # Keyed widgets keep their value while typing; seed them from the saved value when arriving on this page.
        st.session_state.setdefault('w_language', ui.language() if ui.language() in codes else codes[0])
        user = (state.get('auth') or {}).get('user')
        if user:
            c1.text_input('Reviewer (signed in)', value=f'{user["display"]} ({user["user"]})', disabled=True,
                          help='Your decisions are signed with your account key.')
        elif ui.has_name(state):
            c1.markdown(f'**Reviewer on record:** {ui.esc(ui.reviewer())}  \n<span style="color:#4a5568">Change it in the sidebar.</span>',
                        unsafe_allow_html=True)
        else:
            with c1:
                ui.require_name(state, 'approve fixes or run the agent')
        code = c2.selectbox('Page language (chosen by you)', codes, key='w_language', format_func=lambda c: f'{dict(langs)[c]} ({c})',
                            help='Never guessed from the scan. Used only if the page has no language set.')
        st.session_state['al_language'] = code

    with st.container(border=True):
        ui.h2(ui.t('Choose the page'))
        allow = st.checkbox('Allow pages that contain scripts (they are never run)', key='al_allow_scripts',
                            help='Scripts and event handlers are removed from the copy the browser scans and blocked by a '
                                 'security policy. Content that JavaScript would build is therefore not checked.')
        t1, t2, t3 = st.tabs([ui.t('Sample pages'), ui.t('Upload a file'), ui.t('Paste HTML')])
        with t1:
            samples = s.samples()
            labels = {x['id']: x['label'] for x in samples}
            if samples:
                pick = st.selectbox('Sample page', list(labels), format_func=lambda i: f'{labels[i]}  ({i.split("/")[-1]})')
                if st.button(ui.t('Load sample page'), type='primary', key='load_sample'):
                    if ui.run(s.load, None, '', pick, allow):
                        ui.flash('success', 'Sample loaded. Next, run the scan.')
                        st.rerun()
            else:
                st.info('No sample pages were found in the examples folder.')
        with t2:
            file = st.file_uploader('HTML file', type=['html', 'htm'])
            if file is not None and st.button(ui.t('Load uploaded file'), type='primary', key='load_upload'):
                try:
                    text = file.getvalue().decode('utf-8-sig')
                except UnicodeDecodeError:
                    st.error('The file is not valid UTF-8 text.')
                else:
                    if ui.run(s.load, text, file.name, None, allow):
                        ui.flash('success', 'File loaded. Next, run the scan.')
                        st.rerun()
        with t3:
            pasted = st.text_area('HTML source', height=220, placeholder='<!doctype html>\n<html>…')
            if st.button(ui.t('Load pasted HTML'), type='primary', key='load_paste') and pasted.strip():
                if ui.run(s.load, pasted, 'pasted.html', None, allow):
                    ui.flash('success', 'HTML loaded. Next, run the scan.')
                    st.rerun()

    if state['loaded']:
        with st.container(border=True):
            ui.h2('Loaded page')
            ui.metrics([('File', state['source_name'], ''), ('Original fingerprint', state['sha_original'][:12], ''),
                        ('Changed since loading', 'Yes' if state['changed'] else 'No', '')])
            a, b = st.columns(2)
            with a:
                ui.link('scan', 'Continue to scan', ':material/arrow_forward:')
            with b:
                if st.button('Reset to original', key='reset_page'):
                    if ui.run(s.reset):
                        ui.flash('info', 'The working copy was reset to the original.')
                        st.rerun()
            with st.expander('Source preview'):
                st.code(s.file('working')[:6000], language='html')
    ui.footer()
