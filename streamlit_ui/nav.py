"""Page registry: sidebar sections, titles and icons for every operation."""
from __future__ import annotations
import importlib
import streamlit as st
from .i18n import t

# (section, key, title, icon, module)
SPEC = [
    ('', 'home', 'Home', ':material/home:', 'home'),
    ('Workflow', 'load', '1 · Load page', ':material/upload_file:', 'load'),
    ('Workflow', 'scan', '2 · Scan', ':material/search:', 'scan'),
    ('Workflow', 'agent', '★ Agent mode', ':material/smart_toy:', 'agent'),
    ('Workflow', 'review', '3 · Review fixes', ':material/rule:', 'review'),
    ('Workflow', 'verify', '4 · Verify results', ':material/verified:', 'verify'),
    ('Workflow', 'manual', 'Manual review queue', ':material/assignment_late:', 'manual'),
    ('Workflow', 'checklist', 'WCAG manual checklist', ':material/checklist:', 'checklist'),
    ('Workflow', 'preview', 'Page preview', ':material/preview:', 'preview'),
    ('Workflow', 'site', 'Site scan (many pages)', ':material/folder_open:', 'site'),
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
