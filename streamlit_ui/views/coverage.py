from __future__ import annotations
import streamlit as st
from accessloop import catalog as catalog_mod
from .. import ui


def render() -> None:
    s = ui.session()
    cat = s.catalog
    sm = cat['summary']
    ui.page_header('Issue coverage', 'An honest map of every axe rule and all 55 WCAG 2.2 Level A and AA criteria: what is fixed, what is only reported, and what no tool can test.', None, None)
    h = sm['by_handling']
    ui.metrics([('Rules in the engine', sm['total_rules'], ''),
                ('Run on every scan', sm['scanned_today'] + sm['best_practice_optional'], 'good'),
                ('Fix available now', h['live'], 'good'), ('Guidance only', h['guided'], ''),
                ('Not run (deprecated, experimental, AAA)', h['excluded'], '')])
    st.caption(f'Every scan runs {sm["scanned_today"]} WCAG A/AA rules plus {sm["best_practice_optional"]} best-practice rules '
               f'(best practice is on by default). {h["live"]} of the {h["live"] + h["guided"]} rules that apply have a fix; '
               f'the {h["guided"]} others need a structural decision, so AccessLoop explains them instead of editing. '
               f'Of the 55 WCAG 2.2 A/AA criteria, {sm["criteria_manual_only"]} cannot be tested by any automatic tool; '
               'the WCAG manual checklist walks a person through each one.')
    t1, t2, t3 = st.tabs(['Rules', 'WCAG 2.2 criteria', 'Gaps and roadmap'])
    with t1:
        c1, c2, c3 = st.columns([2, 2, 1])
        q = c1.text_input('Search rules', placeholder='e.g. label, contrast, 1.4.3').strip().lower()
        keys = ['all'] + list(catalog_mod.HANDLING)
        pick = c2.selectbox('Show', keys, format_func=lambda k: 'All rules' if k == 'all' else catalog_mod.HANDLING[k])
        scanned = c3.selectbox('Scanned today', ['Any', 'Yes', 'No'])
        rows = []
        for r in cat['rules']:
            if pick != 'all' and r['handling'] != pick:
                continue
            if scanned != 'Any' and r['scanned_today'] != (scanned == 'Yes'):
                continue
            hay = ' '.join([r['rule_id'], r['title'], r['description'], ' '.join(r['wcag'])]).lower()
            if q and q not in hay:
                continue
            rows.append({'Rule': r['rule_id'], 'What it checks': r['title'], 'WCAG': ', '.join(r['wcag']) or 'best practice',
                         'Level': r['level'], 'Handling': catalog_mod.HANDLING[r['handling']], 'Priority': r['priority'] or '',
                         'Scanned today': 'Yes' if r['scanned_today'] else 'No', 'Guidance': r['help_url']})
        st.caption(f'Showing {len(rows)} of {sm["total_rules"]} rules.')
        st.dataframe(rows, hide_index=True, column_config={'Guidance': st.column_config.LinkColumn('Guidance', display_text='axe docs')},
                     **ui.stretch(st.dataframe))
    with t2:
        only = st.checkbox('Only criteria that axe cannot test (need a human)')
        rows = []
        for c in cat['criteria']:
            if only and c['axe_testable']:
                continue
            rows.append({'Criterion': c['criterion'], 'Name': c['name'], 'Level': c['level'], 'Principle': c['principle'],
                         'axe rules': ', '.join(c['axe_rules']) or 'none', 'Next step': c['next_step']['text'],
                         'Why it matters in banking and finance': c['bfsi']})
        st.caption(f'Showing {len(rows)} of {sm["criteria_total"]} criteria.')
        st.dataframe(rows, hide_index=True, **ui.stretch(st.dataframe))
    with t3:
        ui.h2('Known gaps')
        st.write(f'- {len(sm["best_practice_not_scanned"])} best-practice rules run only when "Include best-practice checks" is on (Scan page).')
        st.write(f'- {sm["criteria_manual_only"]} WCAG 2.2 criteria cannot be tested by axe at all and always need a human check.')
        st.write(f'- {sm["criteria_with_planned_check"]} of those have a planned AccessLoop check of their own (keyboard, focus, reflow and similar).')
        ui.h2('Best-practice rules (optional checks)')
        st.write(', '.join(sm['best_practice_not_scanned']))
        st.download_button('Download catalogue (CSV)', catalog_mod.to_csv(cat), file_name='accessloop_issue_catalog.csv', mime='text/csv')
    ui.footer()
