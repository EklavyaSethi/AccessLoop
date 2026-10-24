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


def notice(text: str, kind: str = 'warn') -> None:
    """A notice with guaranteed text contrast (Streamlit's own yellow warning box falls below 4.5:1)."""
    st.markdown(f'<div class="al-notice {esc(kind)}" role="note"><b>{"Note" if kind == "warn" else "Info"}:</b> {esc(text)}</div>',
                unsafe_allow_html=True)


def require_name(state: dict | None = None, action: str = 'make decisions') -> bool:
    """Show why actions are locked when nobody is on record. Returns True when a name is on record."""
    if has_name(state):
        return True
    notice(f'Enter your name in the sidebar to {action}. Every decision and every agent run is recorded against '
           'the person who made it.')
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
        {'success': st.success, 'error': st.error, 'info': st.info, 'warning': notice}[item[0]](item[1])


def badge(text: str, kind: str = 'neutral') -> str:
    return f'<span class="badge {esc(kind)}">{esc(text)}</span>'


def metrics(items: list[tuple]) -> None:
    """items: (label, value, tone) where tone is '', 'good' or 'bad'."""
    cells = ''.join(f'<div class="al-metric {esc(tone)}"><div class="v{" long" if len(str(v)) > 9 else ""}">{esc(str(v))}</div>'
                    f'<div class="l">{esc(t(l))}</div></div>' for l, v, tone in items)
    st.markdown(f'<div class="al-metrics">{cells}</div>', unsafe_allow_html=True)


def severity_html(sev: dict) -> str:
    """Before/after bars per severity. Every bar carries its number as text, so nothing depends on colour or length."""
    order = ('critical', 'serious', 'moderate', 'minor')
    top = max([1] + [sev['baseline'].get(k, 0) for k in order] + [sev['current'].get(k, 0) for k in order])
    rows = []
    for k in order:
        b, c = sev['baseline'].get(k, 0), sev['current'].get(k, 0)
        change = 'no change' if b == c else (f'{b - c} fewer' if c < b else f'{c - b} more')
        rows.append(f'<div class="al-sev"><div class="k"><span class="badge {k}">{k.title()}</span></div>'
                    f'<div class="bars"><div class="b0" style="width:{100 * b / top:.0f}%"></div><div class="b1" style="width:{100 * c / top:.0f}%"></div></div>'
                    f'<div class="nums"><b>{b} → {c}</b><span>{change}</span></div></div>')
    return ('<div class="al-panel al-sevbox" role="group" aria-label="Violations by severity, at first scan and now">'
            '<p class="cap">Violations by severity <span class="key"><i class="k0"></i>at first scan <i class="k1"></i>now</span></p>'
            + ''.join(rows) + '</div>')


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
        cur = step - 1 if step else current_step(state)      # the step this page belongs to
        m = state.get('metrics') or {}
        decided = m.get('verified', 0) + m.get('rejected', 0) + m.get('rolled_back', 0)
        really_done = [bool(state.get('loaded')), bool(state.get('scanned')),
                       bool(state.get('scanned')) and (decided > 0 or m.get('eligible', 1) == 0),
                       m.get('verified', 0) > 0 or m.get('rolled_back', 0) > 0, False]
        parts = []
        for i, n in enumerate(STEPS):
            cls = 'cur' if i == cur else 'done' if really_done[i] else ''
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


def ai_status_html() -> str:
    """One line: which AI drafts the agent's answers, and whether the last connection test worked."""
    import os
    from accessloop import ai_drafts
    from accessloop.ai_advisor import provider
    prov = provider()
    probe = st.session_state.get('al_ai_probe') or {}
    if prov == 'off':
        return (f'{badge("AI off", "neutral")} Drafts come from the page itself (labelled "no AI"). '
                'Switch on Gemini in <b>AI assistant</b> in the sidebar.')
    name = 'Google Gemini' if prov == 'gemini' else 'Local model (Ollama)'
    label = f'{name} · {ai_drafts.model_name()}'
    if probe.get('provider') == prov and probe.get('ok'):
        state = f'{badge("connected", "ok")} tested {esc(probe["checked_at"])}, {probe["seconds"]} s'
    elif probe.get('provider') == prov:
        state = f'{badge("not responding", "bad")} {esc(probe.get("error", "")[:120])}'
    else:
        state = badge('not tested yet', 'warn')
    key_note = '' if prov != 'gemini' or os.getenv('GEMINI_API_KEY') else ' · no API key set'
    return f'{badge("AI on", "info")} <b>{esc(label)}</b> {state}{esc(key_note)}'


def ai_panel() -> None:
    """Sidebar: switch the AI on or off, give it a key for this session, test the connection. The key stays in this
    app's memory only: never written to disk, the audit log or any report."""
    import os
    from accessloop import ai_drafts
    from accessloop.ai_advisor import provider
    with st.expander('AI assistant', icon=':material/auto_awesome:', expanded=False):
        st.markdown(ai_status_html(), unsafe_allow_html=True)
        choices = {'off': 'Off (suggestions from the page, no AI)', 'gemini': 'Google Gemini', 'local': 'Local model (Ollama, nothing leaves this computer)'}
        current = provider()
        pick = st.selectbox('Drafts written by', list(choices), index=list(choices).index(current), format_func=choices.get,
                            key='al_ai_provider')
        if pick != current:
            os.environ['ACCESSLOOP_AI'] = pick
            st.session_state.pop('al_ai_probe', None)
            st.rerun()
        if pick == 'gemini':
            if not os.getenv('GEMINI_API_KEY'):
                key = st.text_input('Gemini API key', type='password', key='al_ai_key',
                                    help='Free key from aistudio.google.com. Kept in memory for this app session only.')
                if key:
                    os.environ['GEMINI_API_KEY'] = key.strip()
                    st.session_state['al_ai_key'] = ''
                    st.rerun()
            else:
                st.caption('API key loaded (hidden).')
            model = st.text_input('Model', value=ai_drafts.model_name(), key='al_ai_model')
            if model.strip() and model.strip() != ai_drafts.model_name():
                os.environ['GEMINI_MODEL'] = model.strip()
        if pick != 'off' and st.button('Test connection', key='al_ai_test'):
            with st.spinner('Asking the model for one test draft…'):
                st.session_state['al_ai_probe'] = ai_drafts.probe()
            st.rerun()
        r = st.session_state.get('al_ai_probe')
        if r and r.get('ok'):
            st.success(f'Working ({r["seconds"]} s). Test draft: “{r["sample"]}”')
        elif r and r.get('error') and pick != 'off':
            st.error(r['error'][:300])
            if r.get('models'):
                st.caption('Models your key can use: ' + ', '.join(r['models']))


def code_context_html(ctx: dict) -> str:
    """Source lines around a fix, with line numbers; the lines the fix touches are marked (not by colour alone)."""
    rows = []
    for ln in ctx.get('lines', []):
        mark = '▶' if ln['changed'] else ' '
        cls = ' class="chg"' if ln['changed'] else ''
        rows.append(f'<div{cls}><span class="ln" aria-hidden="true">{ln["n"]:>5} {mark}</span>{esc(ln["text"]) or " "}</div>')
    span = f'lines {ctx.get("first_line")}–{ctx.get("last_line")} of {ctx.get("total_lines")}'
    return (f'<div class="al-code" role="group" tabindex="0" aria-label="Source code around the fix, {esc(span)}; marked lines change">'
            + ''.join(rows) + '</div>')


def where_is_it(s, proposal_id: str, key: str) -> None:
    """'Where is this on the page?' panel: sentence, breadcrumb, source context, and a picture on demand."""
    try:
        ctx = s.where(proposal_id)
    except Exception as error:  # noqa: BLE001
        st.caption(f'Context unavailable: {error}')
        return
    st.markdown(f'**{esc(ctx["sentence"], quote=False)}**')
    if ctx.get('breadcrumb'):
        st.markdown('<div class="al-crumbs" aria-label="Where it sits">' + ' › '.join(esc(c) for c in ctx['breadcrumb']) + '</div>',
                    unsafe_allow_html=True)
    if ctx.get('lines'):
        st.caption(f'In the code: lines {ctx["first_line"]}–{ctx["last_line"]} of {ctx["total_lines"]} (▶ marks the lines this fix changes).')
        st.markdown(code_context_html(ctx), unsafe_allow_html=True)
    if ctx.get('visible'):
        if st.button('Show it on the page', key=f'pic_{key}', icon=':material/visibility:'):
            st.session_state[f'pic_on_{key}'] = True
        if st.session_state.get(f'pic_on_{key}'):
            try:
                img = s.picture(proposal_id)
            except Exception as error:  # noqa: BLE001
                img, err = None, str(error)
            else:
                err = ''
            if img:
                st.image(img, caption='The element on the rendered page, outlined in red (scripts never run).')
            else:
                st.caption(err or 'This element takes no space on screen (for example it is hidden), so there is nothing to picture.')
    else:
        st.caption('This is a page setting, not something visible on screen.')
