from __future__ import annotations
import streamlit as st
from .. import ui
from .review import _banner


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Verify results', 'After every approved change AccessLoop scans again. A fix counts only if the target problem is gone and no other rule got worse.', 4, state)
    ui.need_scanned(state)
    _banner(state.get('outcome'))
    m = state['metrics']
    delta = m['baseline'] - m['current']
    ui.metrics([('Violation nodes at first scan', m['baseline'], ''), ('Violation nodes now', m['current'], 'good' if delta > 0 else ''),
                ('Net improvement', f'{delta:+d}', 'good' if delta > 0 else 'bad' if delta < 0 else ''),
                ('Rolled back', m['rolled_back'], 'bad' if m['rolled_back'] else '')])

    ui.h2('Severity before and after')
    st.markdown(ui.severity_html(state['severity']), unsafe_allow_html=True)

    ui.h2('Rule by rule')
    counts = state['rule_counts']
    rules = sorted(set(counts['baseline']) | set(counts['current']))
    rows = []
    for r in rules:
        b, c = counts['baseline'].get(r, 0), counts['current'].get(r, 0)
        rows.append({'Rule': r, 'At first scan': b, 'Now': c, 'Change': c - b,
                     'Status': 'Fixed' if c == 0 else 'Improved' if c < b else 'Unchanged' if c == b else 'Worse'})
    if rows:
        st.dataframe(rows, hide_index=True, **ui.stretch(st.dataframe))
    else:
        st.success('No violations detected by the rules that run today.')

    changes = [c for c in state.get('changes', []) if c['kind'] == 'fix']
    if changes:
        ui.h2('Undo one fix')
        st.caption('Undo a single earlier fix and keep all the others. AccessLoop re-scans first; the undo is refused if '
                   'anything other than that fix\'s own rule would get worse, or if a later fix touched the same code.')
        for c in changes:
            a, b = st.columns([4, 1])
            a.markdown(f'**{ui.esc(c["rule"])}** on `{ui.esc(c["selector"])}` · {ui.esc(c["label"])}'
                       + (' · *undone*' if c['status'] == 'reverted' else ''), unsafe_allow_html=True)
            if c['status'] == 'active' and b.button('Undo', key=f'undo_{c["n"]}'):
                with st.spinner('Undoing and re-scanning…'):
                    if ui.run(s.revert, c['n'], ui.reviewer()):
                        st.rerun()

    ui.h2('Decisions so far')
    log = state['fix_log']
    if log:
        st.dataframe([{'Time (UTC)': f['time_utc'].replace('T', ' ').replace('+00:00', ''), 'Rule': f['rule'], 'Element': f['selector'],
                       'Decision': f['decision'], 'Result': f['status'].replace('_', ' '), 'Reviewer': f['reviewer'] or 'not recorded',
                       'Detail': f['detail']} for f in reversed(log)], hide_index=True, **ui.stretch(st.dataframe))
    else:
        st.caption('No decisions yet. Approve or reject a proposal on the Review page.')
    a, b = st.columns(2)
    with a:
        ui.link('review', 'Back to review', ':material/rule:')
    with b:
        ui.link('reports', 'Go to reports', ':material/description:')
    ui.footer()
