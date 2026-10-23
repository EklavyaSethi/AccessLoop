"""Guided manual checks for every WCAG 2.2 A/AA criterion; results go to the audit log and the conformance report."""
from __future__ import annotations
import streamlit as st
from accessloop import manual_tests
from .. import ui


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('WCAG manual checklist', 'Automated rules cover only part of WCAG. Work through each criterion with the '
                   'steps given; every result is saved to the audit log and feeds the conformance report.', None, None)
    ui.need_loaded(state)
    rows = s.worksheet()
    done = [r for r in rows if r.get('result')]
    fails = [r for r in done if r['result'] in ('fail', 'partial')]
    ui.metrics([('Criteria', len(rows), ''), ('Checked', len(done), 'good' if len(done) == len(rows) else ''),
                ('Failed or partly met', len(fails), 'bad' if fails else ''),
                ('Need a person (no automated rule)', sum(1 for r in rows if not r['axe_testable']), '')])
    only = st.radio('Show', ['Needs a person', 'All 55 criteria', 'Not checked yet'], horizontal=True, key='cl_filter')
    labels = dict(manual_tests.RESULTS)
    for r in rows:
        if only == 'Needs a person' and r['axe_testable']:
            continue
        if only == 'Not checked yet' and r.get('result'):
            continue
        status = labels.get(r.get('result', ''), 'Not tested yet')
        with st.expander(f'{r["criterion"]} {r["name"]} (Level {r["level"]}) · {status}'):
            st.markdown(f'**How to test:** {r["how"]}  \n**Passes when:** {r["pass_when"]}')
            if r['axe_rules']:
                st.caption('Automated rules that also cover part of this: ' + ', '.join(r['axe_rules']))
            if r.get('bfsi'):
                st.caption(f'Why it matters in banking: {r["bfsi"]}')
            key = r['criterion'].replace('.', '_')
            options = [v for v, _ in manual_tests.RESULTS]
            current = r.get('result', '')
            choice = st.selectbox('Result', options, index=options.index(current) if current in options else len(options) - 1,
                                  format_func=labels.get, key=f'cl_res_{key}')
            notes = st.text_input('Notes (what you saw, where)', value=r.get('notes', ''), max_chars=500, key=f'cl_note_{key}')
            if st.button('Save result', key=f'cl_save_{key}'):
                if ui.run(s.record_manual, r['criterion'], choice, notes, ui.reviewer()):
                    ui.flash('success', f'Saved {r["criterion"]}: {labels[choice]}.')
                    st.rerun()
            if r.get('time_utc'):
                st.caption(f'Last saved {r["time_utc"]} by {r.get("reviewer") or "not recorded"}.')
    ui.footer()
