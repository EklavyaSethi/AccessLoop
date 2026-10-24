from __future__ import annotations
import streamlit as st
from .. import ui


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Scan the page', 'A sandboxed headless browser opens your page (page scripts never run, no network access) and runs axe-core against WCAG 2.0, 2.1 and 2.2 Level A and AA rules.', 2, state)
    ui.need_loaded(state)
    ui.show_flash()
    cov = s.catalog['summary']

    with st.container(border=True):
        ui.h2(state['source_name'])
        ui.metrics([('Rules run per scan', cov['scanned_today'], ''), ('Rules in the engine', cov['total_rules'], ''),
                    ('Chosen page language', ui.language(), '')])
        bp = st.checkbox(f'Include best-practice checks ({len(cov["best_practice_not_scanned"])} more rules: headings, landmarks, '
                         'lists, tables…)', key='al_bp', value=True, help='Not WCAG failures, but auditors usually report them.')
        ext = st.checkbox('Include AccessLoop browser checks: 320 px reflow, text spacing, visible keyboard focus, '
                          'forced colours, and closed menus/dialogs opened', key='al_ext', value=True,
                          help='About 1–2 seconds more per scan.')
        if st.button(ui.t('Run accessibility scan'), type='primary', key='run_scan'):
            with st.spinner('Scanning in headless Chromium…'):
                ok = ui.run(s.scan, ui.language(), bp, ext)
            if ok:
                ui.flash('success', 'Scan complete. Review the proposed fixes next.')
                st.rerun()

    state = s.state()
    if state['scanned']:
        m = state['metrics']
        ui.h2(ui.t('Scan results'))
        ui.metrics([('Violation nodes found', m['baseline'], 'bad' if m['baseline'] else 'good'),
                    ('Violation nodes now', m['current'], 'good' if m['current'] < m['baseline'] else ''),
                    ('Fixes ready for review', m['eligible'], ''), ('Manual review items', m['manual'], ''),
                    ('Needs a human check', m.get('needs_review', 0), ''),
                    ('Rules that passed', m['passed_rules'], 'good')])
        if state.get('blocked'):
            with st.expander(f'{len(state["blocked"])} resources did not load (the sandbox never fetches from the internet)'):
                st.caption('Styles, fonts or images from these addresses were not part of the scan. Contrast and visibility '
                           'results reflect only what loaded from the page and its own folder.')
                st.code('\n'.join(state['blocked'][:80]))
        st.markdown(ui.severity_html(state['severity']), unsafe_allow_html=True)
        a, b = st.columns(2)
        with a:
            ui.link('review', 'Review proposed fixes', ':material/arrow_forward:')
        with b:
            ui.link('manual', 'See manual review queue', ':material/assignment_late:')
    else:
        with st.expander('Page source'):
            st.code(s.file('working')[:6000], language='html')
    ui.footer()
