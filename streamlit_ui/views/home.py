"""Home: editorial hero, real product figures, the current session and the workflow. Nothing on this page is invented:
every number comes from the rule catalogue or the live session, and empty states say what to do next."""
from __future__ import annotations
import re
from html import escape as esc

import streamlit as st
from .. import ui


def _when(ts: str | None) -> str:
    return (ts or '').replace('T', ' ')[11:16] + ' UTC' if ts else ''


EVENT_TEXT = {'loaded': 'Page loaded', 'scanned': 'Page scanned', 'verified': 'Fix verified and kept',
              'rolled_back': 'Fix rolled back', 'rejected': 'Fix rejected, nothing written', 'refused': 'Change refused',
              'agent_started': 'Agent run started', 'agent_finished': 'Agent run finished', 'ai_drafted': 'Answers drafted',
              'ai_draft_decision': 'Draft used by a person', 'reverted': 'Fix undone', 'reset': 'Session reset',
              'manual_check': 'Manual check recorded', 'approval_requested': 'Waiting for a second approver',
              'blocked': 'Change blocked'}


def _detail(e: dict) -> str:
    text = re.sub(r'^[0-9a-f]{10}-\d+-', '', (e.get('detail') or '').strip())   # drop the internal proposal id
    text = text.split(';')[0]
    return text if len(text) <= 80 else text[:79] + '…'


def _flow(state: dict) -> str:
    m = state.get('metrics') or {}
    scanned = bool(state.get('scanned'))
    eligible, verified = m.get('eligible', 0), m.get('verified', 0)
    steps = [
        ('Scan', 'A real browser and axe-core list every barrier they can detect.',
         'done' if scanned else 'cur'),
        ('Propose', 'Fixed templates prepare an exact, reviewable change.',
         'done' if scanned else ''),
        ('Approve', 'A named person approves each change, or the policy the agent follows.',
         'cur' if scanned and eligible else ('done' if scanned and verified else '')),
        ('Verify', 'The page is scanned again; anything that does not help is undone.',
         'done' if verified else ''),
    ]
    rows = []
    for i, (name, text, cls) in enumerate(steps, 1):
        tag = {'cur': '<span class="st">current step</span>', 'done': '<span class="st ok">done</span>'}.get(cls, '')
        mark = '✓' if cls == 'done' else str(i)
        aria = ' aria-current="step"' if cls == 'cur' else ''
        rows.append(f'<li class="{cls}"{aria}><span class="dot" aria-hidden="true">{mark}</span>'
                    f'<div><b>{name}{tag}</b><span class="d">{text}</span></div></li>')
    return '<ol class="al-flow" aria-label="Workflow">' + ''.join(rows) + '</ol>'


def _session_panel(state: dict) -> str:
    if not state.get('loaded'):
        return ('<div class="al-panel"><p class="cap">Current session</p><h2>No page loaded yet</h2>'
                '<p>Load one of the sample banking pages or your own HTML file, then scan it. AccessLoop never changes your '
                'original file: it works on a copy, and every change waits for a person\'s approval.</p></div>')
    name = esc(state.get('source_name') or 'page')
    if not state.get('scanned'):
        return (f'<div class="al-panel"><p class="cap">Current session</p><p class="big"><b>{name}</b> is loaded and '
                'ready to scan.</p><p>Run the scan to see every barrier the engine can detect, by severity.</p></div>')
    m = state['metrics']
    base, cur = m['baseline'], m['current']
    pct = round(100 * (base - cur) / base) if base else 0
    return (f'<div class="al-panel"><p class="cap">Current session · {name}</p>'
            f'<p class="big">Violations <b>{base} → {cur}</b>. <b>{m["verified"]}</b> fixes verified and kept, '
            f'<b>{m["eligible"]}</b> waiting for approval.</p>'
            f'<div class="al-bar" role="img" aria-label="{pct}% of the violations found at the first scan are fixed">'
            f'<span style="width:{max(0, min(pct, 100))}%"></span></div>'
            f'<p>{pct}% of the first scan\'s violations resolved · {m["rolled_back"]} rolled back · {m["rejected"]} rejected · '
            f'{m["manual"]} need a person.</p>'
            f'<p style="margin-top:14px"><b style="color:var(--ink)">Next:</b> '
            f'{"review the fixes waiting for approval, or let the agent apply the low-risk ones." if m["eligible"] else "download the evidence, or check the manual review queue."}</p></div>')


def _activity(state: dict) -> str:
    events = [e for e in (state.get('events') or []) if e.get('event') in EVENT_TEXT][:6]
    if not events:
        body = ('<p>No activity yet. Every scan, decision and agent step will appear here, and in the signed audit log.</p>')
    else:
        rows = ''.join(f'<li><span class="txt"><span class="what">{esc(EVENT_TEXT[e["event"]])}</span>'
                       f'<span class="sub">{esc(_detail(e))}</span></span>'
                       f'<span class="when">{esc(_when(e.get("timestamp_utc")))}</span></li>' for e in events[:5])
        body = f'<ul class="al-rows">{rows}</ul>'
    return f'<div class="al-panel"><p class="cap">Recent activity</p>{body}</div>'


def render() -> None:
    s = ui.session()
    state = s.state()
    summary = s.catalog['summary']
    live, total = summary['by_handling']['live'], summary['total_rules']
    checked = summary['scanned_today'] + summary['best_practice_optional']
    st.markdown("""
<div class="al-hero">
  <div class="al-kicker">Accessibility engineering · Human-approved repairs</div>
  <h1>Fix accessibility issues.<br><em>Prove every fix.</em></h1>
  <p>Find accessibility barriers, review safe source-level repairs, approve every change, and verify the results with
  browser-based evidence.</p>
</div>""", unsafe_allow_html=True)
    a, b, _ = st.columns([1.1, 1.1, 4])
    with a:
        if st.button('Start a scan', type='primary', icon=':material/arrow_forward:', key='home_start'):
            from .. import nav
            st.switch_page(nav.PAGES['load'])
    with b:
        ui.link('how', 'How it works', ':material/help:')

    pending = (state.get('metrics') or {}).get('eligible') if state.get('scanned') else None
    st.markdown(f"""
<div class="al-strip">
  <div><div class="n">{live}</div><div class="l">repair templates, each proven in a real browser</div></div>
  <div><div class="n">{checked}</div><div class="l">axe-core rules checked per scan, of {total} in the engine</div></div>
  <div><div class="n">{summary['criteria_total']}</div><div class="l">WCAG 2.2 A and AA criteria mapped; {summary['criteria_axe_testable']} automatable, the rest on a manual checklist</div></div>
  <div><div class="n">{pending if pending is not None else '–'}</div><div class="l">{'fixes waiting for your approval' if pending is not None else 'fixes waiting for approval (scan a page first)'}</div></div>
</div>
<div class="al-board">
  {_session_panel(state)}
  <div class="al-panel"><p class="cap">Workflow</p>{_flow(state)}</div>
</div>
<div class="al-board b3">
  {_activity(state)}
  <div class="al-panel"><p class="cap">Governance</p><h2 class="sm">Nothing changes without a name on it</h2>
    <p>Every change is approved by a named person, or by a policy that person approved for the agent. Each fix is kept
    only if a fresh scan shows it helped and nothing got worse; otherwise it is undone byte for byte. Every step goes into a
    hash-chained, signed audit log.</p></div>
  <div class="al-panel"><p class="cap">Coverage</p><h2 class="sm">{live} of {total} rules repairable</h2>
    <div class="al-bar" role="img" aria-label="{live} of {total} engine rules have a repair template"><span style="width:{round(100 * live / total)}%"></span></div>
    <p>{summary['by_handling']['guided']} more are explained but need a structural decision; {summary['by_handling']['excluded']} are
    deprecated, experimental or AAA-only. Automated checks cover part of WCAG: this is not a conformance certificate.</p></div>
</div>""", unsafe_allow_html=True)
    c1, c2, c3, _ = st.columns([1, 1, 1, 2])
    with c1:
        ui.link('agent', 'Open agent mode', ':material/smart_toy:')
    with c2:
        ui.link('reports', 'Reports and evidence', ':material/description:')
    with c3:
        ui.link('coverage', 'Full rule coverage', ':material/fact_check:')
    ui.footer()
