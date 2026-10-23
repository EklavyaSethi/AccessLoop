from __future__ import annotations
import streamlit as st
from .. import ui


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Audit trail', 'Every action is recorded with a time and the fingerprint (SHA-256) of the working file, so changes can be traced and checked.', None, None)
    ui.need_loaded(state)
    audit = state.get('audit') or {}
    ui.metrics([('Original fingerprint', state['sha_original'][:12], ''), ('Current fingerprint', state['sha_current'][:12], ''),
                ('Changed', 'Yes' if state['changed'] else 'No', ''),
                ('Audit log chain', 'Verified' if audit.get('verified') else 'BROKEN', 'good' if audit.get('verified') else 'bad')])
    st.caption(f'{audit.get("entries", 0)} entries, append-only. Each entry stores the hash of the one before it, so any edit, '
               f'deletion or reordering is detected. Head hash: {audit.get("head_sha256") or "-"}')
    ui.h2('Events')
    events = state['events']
    if events:
        st.dataframe([{'Time (UTC)': e['timestamp_utc'].replace('T', ' ').replace('+00:00', ''), 'Event': e['event'], 'Detail': e['detail'],
                       'Working file': (e.get('working_sha256') or '')[:12]} for e in events], hide_index=True, **ui.stretch(st.dataframe))
    else:
        st.caption('No events yet.')
    ui.h2('Fix decisions')
    log = state['fix_log']
    if log:
        for f in reversed(log):
            with st.container(border=True):
                st.markdown(ui.badge(f['decision'], 'ok' if f['status'] == 'verified' else 'bad' if f['status'] == 'rolled_back' else 'info')
                            + ui.badge(f['rule'], 'neutral') + ui.badge(f['status'].replace('_', ' '), 'neutral'), unsafe_allow_html=True)
                st.caption(f'{f["time_utc"]} · {f["selector"]} · reviewer: {f["reviewer"] or "not recorded"}')
                st.markdown(ui.diff_html([{'kind': 'del', 'text': f['before']}, {'kind': 'add', 'text': f['after']}]), unsafe_allow_html=True)
                st.caption(f['detail'])
    else:
        st.caption('No decisions recorded yet.')
    ui.h2('Integrity')
    st.code(f'Original SHA-256: {state["sha_original"]}\nCurrent  SHA-256: {state["sha_current"]}')
    ui.footer()
