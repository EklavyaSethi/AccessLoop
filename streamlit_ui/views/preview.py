from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from accessloop.htmlsource import Doc, scan_copy
from .. import ui


def _safe(html: str) -> str:
    # The same sandboxed copy the scanner uses: scripts, handlers and active URLs removed, scripts blocked by policy.
    return scan_copy(Doc(html))


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Page preview', 'The original and the current working copy side by side. Previews never run page '
                   'scripts and never fetch anything from the internet.', None, None)
    ui.need_loaded(state)
    tab_visual, tab_live = st.tabs(['Visual comparison (changes outlined)', 'Interactive preview'])
    with tab_visual:
        if st.button(ui.t('Render both versions'), type='primary', key='render_shots'):
            with st.spinner('Rendering in the sandboxed browser…'):
                try:
                    st.session_state['al_shots'] = (state['sha_current'], *s.screenshots())
                except Exception as error:  # noqa: BLE001
                    st.error(str(error))
        shots = st.session_state.get('al_shots')
        if shots and shots[0] == state['sha_current']:
            a, b = st.columns(2)
            a.image(shots[1], caption='Original', **ui.stretch(a.image))
            b.image(shots[2], caption='Repaired (changed elements outlined in red)', **ui.stretch(b.image))
        elif shots:
            st.caption('The working copy changed since the last render. Render again to compare.')
    with tab_live:
        a, b = st.columns(2)
        with a:
            ui.h2('Original')
            components.html(_safe(s.file('original')), height=620, scrolling=True)
        with b:
            ui.h2('Current working copy')
            components.html(_safe(s.file('working')), height=620, scrolling=True)
    if state['changed']:
        st.success('The working copy differs from the original. See the Audit trail for each change.')
    else:
        st.caption('The working copy is identical to the original.')
    ui.footer()
