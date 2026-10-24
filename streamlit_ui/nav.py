"""Page registry: sidebar sections, titles and icons for every operation."""
from __future__ import annotations
import importlib
import streamlit as st
from .i18n import t

# (section, key, title, icon, module)
SPEC = [
    ('', 'home', 'Home', ':material/home:', 'home'),
    ('Workspace', 'load', '1 · Load page', ':material/upload_file:', 'load'),
    ('Workspace', 'scan', '2 · Scan', ':material/search:', 'scan'),
    ('Workspace', 'agent', '★ Agent mode', ':material/smart_toy:', 'agent'),
    ('Workspace', 'review', '3 · Review fixes', ':material/rule:', 'review'),
    ('Workspace', 'verify', '4 · Verify results', ':material/verified:', 'verify'),
    ('Review', 'manual', 'Manual review queue', ':material/assignment_late:', 'manual'),
    ('Review', 'checklist', 'WCAG manual checklist', ':material/checklist:', 'checklist'),
    ('Review', 'preview', 'Page preview', ':material/preview:', 'preview'),
    ('Review', 'site', 'Site scan (many pages)', ':material/folder_open:', 'site'),
    ('Evidence', 'reports', 'Reports and downloads', ':material/description:', 'reports'),
    ('Evidence', 'audit', 'Audit trail', ':material/history:', 'audit'),
    ('Evidence', 'trace', 'Agent trace', ':material/timeline:', 'trace'),
    ('Reference', 'coverage', 'Issue coverage', ':material/fact_check:', 'coverage'),
    ('Reference', 'how', 'How it works', ':material/help:', 'how'),
]
PAGES: dict = {}
TITLES = {key: title for _, key, title, _, _ in SPEC}


def build() -> dict:
    sections: dict[str, list] = {}
    for section, key, title, icon, module in SPEC:
        render = importlib.import_module(f'streamlit_ui.views.{module}').render
        page = st.Page(render, title=t(title), icon=icon, url_path=None if key == 'home' else key, default=(key == 'home'))
        PAGES[key] = page
        sections.setdefault(t(section), []).append(page)
    return sections


def brand() -> None:
    from .theme import LOGO_SVG
    mark = LOGO_SVG.replace('width="40" height="40"', 'width="28" height="28" aria-hidden="true" focusable="false"')
    st.markdown('<div class="al-brand">' + mark + '<div><span class="w">AccessLoop</span>'
                '<span class="s">Accessibility repair, human approved</span></div></div>', unsafe_allow_html=True)


def sidebar() -> None:
    """Our own sidebar links. Streamlit's generated menu nests section headers inside its <ul>, which screen readers
    report as a broken list (axe: list / listitem), so the app hides it and draws plain links grouped by section."""
    section = None
    for sec, key, title, icon, _ in SPEC:
        if sec != section:
            section = sec
            if sec:
                st.markdown(f'<p class="al-navsec">{t(sec)}</p>', unsafe_allow_html=True)
        st.page_link(PAGES[key], label=t(title), icon=icon)
