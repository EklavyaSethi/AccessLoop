"""Site scan: many pages at once, problems grouped by the shared template they probably come from."""
from __future__ import annotations
import streamlit as st
from accessloop import site
from .. import ui


def render() -> None:
    s = ui.session()
    ui.page_header('Site scan', 'Upload several pages or a .zip of a site. AccessLoop scans every page, groups identical '
                   'problems across pages (usually a shared header, footer or form template) and can apply the automatic '
                   'fixes to every page, each one re-verified.', None, None)
    if s.auth_required():
        st.stop()
    files = st.file_uploader('HTML files or a .zip', type=['html', 'htm', 'zip'], accept_multiple_files=True, key='site_files')
    c1, c2, c3 = st.columns(3)
    bp = c1.checkbox('Best-practice checks', value=True, key='site_bp')
    ext = c2.checkbox('AccessLoop browser checks', value=False, key='site_ext', help='Slower: about 2 s more per page.')
    fix = c3.checkbox('Apply automatic fixes to every page', value=False, key='site_fix',
                      help='Only fixes that need no typed text. Each is re-verified; results come as a zip.')
    if files and st.button(ui.t('Scan site'), type='primary', key='site_go'):
        pages = []
        for f in files:
            pages += site.read_upload(f.name, f.getvalue())
        bar = st.progress(0.0, text='Starting…')

        def progress(i, n, name):
            bar.progress(i / max(n, 1), text=f'Page {i + 1} of {n}: {name}')
        reviewer = ui.reviewer() or 'scan only (no changes)'
        if (s.state().get('auth') or {}).get('user'):
            reviewer = s.reviewer
        st.session_state['site_result'] = site.scan_site(pages, bp, ext, True, fix, reviewer, progress)
        bar.progress(1.0, text=f'Done: {len(pages)} pages.')
    res = st.session_state.get('site_result')
    if not res:
        ui.footer()
        return
    rows = res['pages']
    ok = [r for r in rows if r['status'] == 'scanned']
    shared = [g for g in res['groups'] if g['likely_shared_template']]
    ui.metrics([('Pages scanned', len(ok), ''), ('Refused or failed', len(rows) - len(ok), 'bad' if len(rows) > len(ok) else ''),
                ('Violation nodes', sum(r['violations'] for r in ok), ''),
                ('Problems shared by 2+ pages', len(shared), '')])
    ui.h2('Problems grouped by shared template')
    st.caption('The same rule on the same element markup across several pages almost always comes from one template: fix it once there.')
    st.dataframe([{'Pages': g['pages'], 'Occurrences': g['occurrences'], 'Rule': g['rule'], 'Element': g['element'],
                   'Impact': g['impact'], 'Fix available': 'yes' if g['fix_available'] else 'needs a person',
                   'Example pages': ', '.join(g['example_pages'])} for g in res['groups']], hide_index=True,
                 **ui.stretch(st.dataframe))
    ui.h2('Pages')
    st.dataframe(rows, hide_index=True, **ui.stretch(st.dataframe))
    if res['files']:
        st.download_button('Download repaired pages, patches and audit logs (.zip)', site.result_zip(res),
                           file_name='accessloop_site_fixes.zip', mime='application/zip', type='primary')
    ui.footer()
