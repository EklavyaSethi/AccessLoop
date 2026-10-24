from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from accessloop import catalog as catalog_mod
from accessloop.web import report as report_mod
from .. import ui


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Reports and downloads', 'Everything an auditor, a teammate or a regulator-facing reviewer needs, generated from this session.', 5, state)
    ui.need_scanned(state)
    html = report_mod.build_html(s.report_payload())
    base = state['source_name'].rsplit('.', 1)[0] or 'page'

    with st.container(border=True):
        ui.h2('Session reports')
        a, b = st.columns(2)
        a.download_button('Evidence report (HTML, print to PDF)', html, file_name=f'{base}_evidence_report.html', mime='text/html', type='primary')
        b.download_button('Evidence record (JSON)', s.report_json(), file_name=f'{base}_evidence.json', mime='application/json')
        c, d = st.columns(2)
        c.download_button('Repaired page (HTML)', s.file('working'), file_name=f'{base}_repaired.html', mime='text/html')
        made = s.new_files()
        if made:
            st.download_button(f'Repaired page + {len(made)} new file(s) it needs (.zip)', s.bundle(),
                               file_name=f'{base}_repaired_with_files.zip', mime='application/zip', type='primary',
                               help='Files the fixes created, such as captions: ' + ', '.join(made))
        d.download_button('Original page (HTML)', s.file('original'), file_name=f'{base}_original.html', mime='text/html')
        st.caption('To make a PDF, open the evidence report in your browser and choose Print, then Save as PDF.')

    with st.container(border=True):
        ui.h2('Standard formats')
        st.caption('For developers, auditors and issue trackers. Every file is generated from this session.')
        cols = st.columns(3)
        items = [('agent-html', 'Agent run report (HTML, print to PDF)', 'Policy, every step, every change, audit hashes.'),
                 ('agent-json', 'Agent run record (JSON)', 'Machine-readable; signed when you are signed in.'),
                 ('patch', 'Code change (git patch)', 'Apply with git am or git apply.'),
                 ('acr', 'Conformance report (VPAT-style)', 'All 55 WCAG 2.2 A/AA criteria, using your manual checks too.'),
                 ('jira', 'Jira import (CSV)', 'One ticket per remaining issue.'),
                 ('github', 'GitHub issues (Markdown + gh script)', 'One issue per remaining issue.'),
                 ('junit', 'Test results (JUnit XML)', 'Shown natively by CI systems.')]
        for i, (kind, label, help_text) in enumerate(items):
            try:
                content, name, mime = s.export(kind)
            except Exception as error:  # noqa: BLE001
                cols[i % 3].caption(f'{label}: {error}')
                continue
            if not content:
                cols[i % 3].caption(f'{label}: nothing to export yet (no changes approved).')
                continue
            cols[i % 3].download_button(label, content, file_name=name, mime=mime.split(';')[0], help=help_text,
                                        key=f'export_{kind}')

    with st.container(border=True):
        ui.h2('Issue catalogue')
        e, f = st.columns(2)
        e.download_button('Catalogue (CSV)', catalog_mod.to_csv(s.catalog), file_name='accessloop_issue_catalog.csv', mime='text/csv')
        f.download_button('Catalogue (Markdown)', catalog_mod.to_markdown(s.catalog), file_name='accessloop_issue_catalog.md', mime='text/markdown')

    with st.expander('Preview the evidence report', expanded=True):
        components.html(html, height=900, scrolling=True)
    ui.footer()
