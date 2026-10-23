"""Shared helpers for the Streamlit pages. Dynamic text is always HTML-escaped before it reaches unsafe_allow_html."""
from __future__ import annotations
import inspect
from html import escape as esc
from pathlib import Path

import streamlit as st

from accessloop.web.server import Session
from . import theme
from .i18n import t, page as _page_text

ROOT = Path(__file__).resolve().parent.parent
STEPS = ['Load', 'Scan', 'Review', 'Verify', 'Report']


def stretch(fn) -> dict:
    """Full-width keyword that works on both older and newer Streamlit releases."""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return {}
    if 'use_container_width' in params:
        return {'use_container_width': True}
    if 'width' in params:
        return {'width': 'stretch'}
    return {}


def setup() -> None:
    st.markdown(theme.CSS, unsafe_allow_html=True)


def session() -> Session:
    if 'al_session' not in st.session_state:
        st.session_state['al_session'] = Session(ROOT)
    return st.session_state['al_session']


def reviewer() -> str:
    return (st.session_state.get('al_reviewer') or '').strip()


def has_name(state: dict | None = None) -> bool:
    """A person is on record: signed in, or a real name typed in the sidebar (at least two characters, one a letter)."""
    if ((state or {}).get('auth') or {}).get('user'):
        return True
    name = reviewer()
    return len(name) >= 2 and any(ch.isalpha() for ch in name)


def require_name(state: dict | None = None, action: str = 'make decisions') -> bool:
    """Show why actions are locked when nobody is on record. Returns True when a name is on record."""
    if has_name(state):
        return True
    st.warning(f'Enter your name in the sidebar to {action}. Every decision and every agent run is recorded against '
               'the person who made it.', icon=':material/badge:')
    return False


def language() -> str:
    return st.session_state.get('al_language', 'en')


def run(action, *args, **kwargs) -> bool:
    """Run a Session action; show any error in place instead of crashing the page."""
    try:
        action(*args, **kwargs)
        return True
    except Exception as error:  # noqa: BLE001 - ApiError / WorkflowError / scanner failures
        st.error(str(error) or type(error).__name__)
        return False


def flash(kind: str, message: str) -> None:
    st.session_state['al_flash'] = (kind, message)


def show_flash() -> None:
    item = st.session_state.pop('al_flash', None)
    if item:
        {'success': st.success, 'error': st.error, 'info': st.info, 'warning': st.warning}[item[0]](item[1])


def badge(text: str, kind: str = 'neutral') -> str:
    return f'<span class="badge {esc(kind)}">{esc(text)}</span>'


def metrics(items: list[tuple]) -> None:
    """items: (label, value, tone) where tone is '', 'good' or 'bad'."""
    cells = ''.join(f'<div class="al-metric {esc(tone)}"><div class="v">{esc(str(v))}</div><div class="l">{esc(t(l))}</div></div>'
                    for l, v, tone in items)
    st.markdown(f'<div class="al-metrics">{cells}</div>', unsafe_allow_html=True)


def diff_html(lines: list[dict]) -> str:
    marks = {'add': '+ ', 'del': '- ', 'ctx': '  ', 'meta': ''}
    lines = [x for x in lines if x['kind'] != 'meta']
    rows = ''.join(f'<div class="{esc(x["kind"])}">{marks.get(x["kind"], "")}{esc(x["text"])}</div>' for x in lines)
    return f'<div class="al-diff" role="group" aria-label="Proposed change">{rows}</div>'


def current_step(state: dict) -> int:
    if not state.get('loaded'):
        return 0
    if not state.get('scanned'):
        return 1
    return 2 if state['metrics']['eligible'] else 4


def page_header(title: str, subtitle: str, step: int | None = None, state: dict | None = None) -> None:
    title, subtitle, lang = _page_text(title, subtitle)
    eyebrow = (f'चरण {step} / 5' if lang == 'hi' else f'Step {step} of 5') if step else 'AccessLoop'
    st.markdown(f'<div class="al-head" lang="{lang}"><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1>'
                f'<p>{esc(subtitle)}</p></div>', unsafe_allow_html=True)
    if state is not None:
        cur = current_step(state)
        parts = []
        for i, n in enumerate(STEPS):
            cls = 'done' if i < cur else 'cur' if i == cur else ''
            aria = ' aria-current="step"' if i == cur else ''
            parts.append(f'<li class="{cls}"{aria}><span class="n" aria-hidden="true">{i + 1}</span>{esc(t(n))}</li>')
        items = ''.join(parts)
        st.markdown(f'<ol class="al-steps" aria-label="Workflow progress">{items}</ol>', unsafe_allow_html=True)


def h2(text: str) -> None:
    """Section heading. Streamlit's st.subheader renders <h3>, which skips a level after the page's <h1>."""
    st.markdown(f'<h2 class="al-h2">{esc(t(text))}</h2>', unsafe_allow_html=True)


def link(key: str, label: str | None = None, icon: str | None = None) -> None:
    from . import nav
    page = nav.PAGES.get(key)
    if page is not None:
        st.page_link(page, label=label or nav.TITLES[key], icon=icon)


def need_loaded(state: dict) -> None:
    if not state['loaded']:
        st.info('No page is loaded yet. Load a sample or upload an HTML file first.')
        link('load', 'Go to Load page', ':material/upload_file:')
        st.stop()


def need_scanned(state: dict) -> None:
    need_loaded(state)
    if not state['scanned']:
        st.info('This page has not been scanned yet. Run the scan first.')
        link('scan', 'Go to Scan page', ':material/search:')
        st.stop()


def footer() -> None:
    st.markdown('<div class="al-foot">AccessLoop is a proof of concept and does not certify WCAG conformance. Automated checks find '
                'only part of the barriers real people face, so keyboard, screen-reader and human usability testing remain necessary.</div>',
                unsafe_allow_html=True)
