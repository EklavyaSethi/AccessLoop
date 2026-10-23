from __future__ import annotations
import streamlit as st
from .. import ui


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Manual review queue', 'Issues AccessLoop will not edit automatically: either unsupported yet, or too ambiguous to fix without guessing.', None, None)
    ui.need_scanned(state)
    items = state['unresolved']
    ui.metrics([('Items in the queue', len(items), 'bad' if items else 'good'), ('Inconclusive axe checks', state['metrics']['incomplete'], '')])
    if not items:
        st.success('No remaining automated findings.')
        ui.footer()
        return
    c1, c2 = st.columns(2)
    impacts = sorted({i['impact'] for i in items})
    handlings = sorted({i['handling_label'] for i in items})
    f_imp = c1.multiselect('Severity', impacts, default=impacts)
    f_han = c2.multiselect('AccessLoop handling', handlings, default=handlings)
    shown = [i for i in items if i['impact'] in f_imp and i['handling_label'] in f_han]
    st.caption(f'Showing {len(shown)} of {len(items)}.')
    for i in shown:
        with st.container(border=True):
            tags = ui.badge(i['impact'], i['impact']) + ui.badge(i['rule'], 'neutral') + ui.badge(i['handling_label'], 'info')
            if i['wcag']:
                tags += ui.badge('WCAG ' + ', '.join(i['wcag']), 'neutral')
            st.markdown(f'<div><b>{ui.esc(i["help"])}</b></div><div>{tags}</div>', unsafe_allow_html=True)
            st.caption(f'Element: {i["selector"]}')
            if i['note']:
                st.write(i['note'])
            if i['help_url']:
                st.markdown(f'[Open axe guidance for {i["rule"]}]({i["help_url"]})')
    if state['metrics']['incomplete']:
        st.warning(f'{state["metrics"]["incomplete"]} axe check(s) were inconclusive and need a manual check.')
    ui.footer()
