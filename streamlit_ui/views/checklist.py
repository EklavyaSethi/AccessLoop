"""Guided manual checks for every WCAG 2.2 A/AA criterion; results go to the audit log and the conformance report.

Designed to feel light: a progress ring and per-principle bars show how far you are, "one at a time" mode walks you
through the next unchecked criterion, and each criterion is answered with a single click (Pass, Fail, Partly, N/A)."""
from __future__ import annotations
from html import escape as esc

import streamlit as st
from accessloop import manual_tests
from .. import ui

PRINCIPLES = [('Perceivable', 'Can people see or hear everything?'), ('Operable', 'Can people use it with a keyboard and enough time?'),
              ('Understandable', 'Is it clear what to do and how to fix mistakes?'), ('Robust', 'Does it work with assistive technology?')]
QUICK = [('pass', 'Pass', ':material/check_circle:'), ('fail', 'Fail', ':material/cancel:'),
         ('partial', 'Partly', ':material/contrast:'), ('na', 'N/A', ':material/block:')]
TONE = {'pass': 'ok', 'fail': 'bad', 'partial': 'warn', 'na': 'neutral'}


def _ring(done: int, total: int) -> str:
    pct = done / total if total else 0
    r, c = 52, 2 * 3.14159 * 52
    return (f'<svg width="132" height="132" viewBox="0 0 132 132" role="img" aria-label="{done} of {total} criteria checked">'
            f'<circle cx="66" cy="66" r="{r}" fill="none" stroke="#eceff3" stroke-width="10"/>'
            f'<circle cx="66" cy="66" r="{r}" fill="none" stroke="#132843" stroke-width="10" stroke-linecap="round" '
            f'stroke-dasharray="{c * pct:.1f} {c:.1f}" transform="rotate(-90 66 66)" class="al-ring"/>'
            f'<text x="66" y="62" text-anchor="middle" font-family="Georgia,serif" font-size="30" fill="#18202b">{done}</text>'
            f'<text x="66" y="84" text-anchor="middle" font-size="12" fill="#5b6370">of {total} checked</text></svg>')


def _overview(rows: list[dict]) -> str:
    done = [r for r in rows if r.get('result')]
    bars = []
    for name, question in PRINCIPLES:
        group = [r for r in rows if r['principle'] == name]
        d = sum(1 for r in group if r.get('result'))
        f = sum(1 for r in group if r.get('result') in ('fail', 'partial'))
        pct = round(100 * d / len(group)) if group else 0
        bars.append(f'<div class="al-pbar"><div class="top"><b>{name}</b><span>{d}/{len(group)}'
                    f'{f" · {f} to fix" if f else ""}</span></div>'
                    f'<div class="al-bar" role="img" aria-label="{name}: {d} of {len(group)} checked"><span style="width:{pct}%"></span></div>'
                    f'<p>{question}</p></div>')
    fails = sum(1 for r in done if r['result'] in ('fail', 'partial'))
    passes = sum(1 for r in done if r['result'] == 'pass')
    return (f'<div class="al-board al-cl"><div class="al-panel al-ringbox">{_ring(len(done), len(rows))}'
            f'<div><p class="cap">Your progress</p><p class="big">{passes} passed · {fails} to fix</p>'
            f'<p>Only {sum(1 for r in rows if not r["axe_testable"])} of the {len(rows)} criteria have no automated rule at all. '
            'Start with those: "One at a time" picks them first.</p></div></div>'
            f'<div class="al-panel"><p class="cap">By principle</p>{"".join(bars)}</div></div>')


def _answer(s, r: dict, key: str, notes_key: str) -> None:
    """One-click result buttons; the notes box is optional."""
    named = st.session_state.get('_cl_named', False)
    cols = st.columns(len(QUICK) + 1)
    for col, (value, label, icon) in zip(cols, QUICK):
        current = r.get('result') == value
        if col.button(label, key=f'cl_{value}_{key}', icon=icon, type='primary' if current else 'secondary',
                      help=f'Record "{label}" for {r["criterion"]}', disabled=not named):
            if ui.run(s.record_manual, r['criterion'], value, st.session_state.get(notes_key, r.get('notes', '')), ui.reviewer()):
                ui.flash('success', f'Saved {r["criterion"]} {r["name"]}: {label}.')
                st.rerun()


def _criterion(s, r: dict, prefix: str) -> None:
    key = prefix + r['criterion'].replace('.', '_')
    notes_key = f'cl_note_{key}'
    st.markdown(f'<div class="al-step"><span class="lbl">How to test</span>{esc(r["how"])}</div>'
                f'<div class="al-step ok"><span class="lbl">Passes when</span>{esc(r["pass_when"])}</div>', unsafe_allow_html=True)
    if r.get('bfsi'):
        st.caption(f'Why it matters in banking: {r["bfsi"]}')
    if r['axe_rules']:
        st.caption('Also partly covered by the automated rules: ' + ', '.join(r['axe_rules']))
    st.text_input('Notes (optional: what you saw, where)', value=r.get('notes', ''), max_chars=500, key=notes_key)
    _answer(s, r, key, notes_key)
    if r.get('time_utc'):
        st.caption(f'Last saved {r["time_utc"].replace("T", " ")[:16]} UTC by {r.get("reviewer") or "not recorded"}.')


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('WCAG manual checklist', 'Automated rules cover only part of WCAG. Check the rest by hand, one '
                   'criterion at a time; every answer is saved to the audit log and feeds the conformance report.', None, None)
    ui.need_loaded(state)
    ui.show_flash()
    rows = s.worksheet()
    st.markdown(_overview(rows), unsafe_allow_html=True)
    st.session_state['_cl_named'] = ui.require_name(state, 'record results')

    mode = st.radio('View', ['One at a time', 'By principle', 'Everything'], horizontal=True, key='cl_mode',
                    help='"One at a time" shows the next criterion that still needs a person; answer it and the next appears.')
    labels = dict(manual_tests.RESULTS)
    if mode == 'One at a time':
        skipped = st.session_state.setdefault('cl_skipped', [])
        todo = sorted((r for r in rows if not r.get('result')), key=lambda r: (r['criterion'] in skipped, r['axe_testable'], r['criterion']))
        if not todo:
            st.markdown('<div class="al-panel"><p class="cap">All done</p><h2 class="sm">Every criterion has a result</h2>'
                        '<p>Download the conformance report from Reports and downloads, or switch to "By principle" to '
                        'review or change an answer.</p></div>', unsafe_allow_html=True)
            ui.link('reports', 'Reports and downloads', ':material/description:')
        else:
            r = todo[0]
            auto = 'partly checked by automated rules' if r['axe_testable'] else 'needs a person: no automated rule'
            manual_left = sum(1 for x in todo if not x['axe_testable'])
            manual_total = sum(1 for x in rows if not x['axe_testable'])
            left = (f'{manual_left} of {manual_total} manual-only criteria left' if manual_left
                    else f'manual-only done · {len(todo)} partly automated left')
            st.markdown(f'<div class="al-panel al-focus"><p class="cap">Next · {left} · {esc(r["principle"])}</p>'
                        f'<h2>{esc(r["criterion"])} {esc(r["name"])}</h2><p>Level {esc(r["level"])} · {auto}</p></div>',
                        unsafe_allow_html=True)
            with st.container(border=True):
                _criterion(s, r, 'one_')
                if st.button('Skip for now', key=f'cl_skip_{r["criterion"]}', icon=':material/skip_next:',
                             help='Moves on without recording anything; it comes back at the end.'):
                    skipped.append(r['criterion'])
                    st.rerun()
        ui.footer()
        return

    only_open = st.toggle('Hide criteria that already have a result', key='cl_open')
    groups = PRINCIPLES if mode == 'By principle' else [('Everything', '')]
    tabs = st.tabs([f'{n} ({sum(1 for r in rows if r["principle"] == n and not r.get("result"))} open)' for n, _ in groups]) \
        if mode == 'By principle' else [st.container()]
    for tab, (name, _) in zip(tabs, groups):
        with tab:
            for r in rows:
                if mode == 'By principle' and r['principle'] != name:
                    continue
                if only_open and r.get('result'):
                    continue
                status = labels.get(r.get('result', ''), 'Not tested yet')
                mark = {'pass': '✓', 'fail': '✗', 'partial': '◐', 'na': '–'}.get(r.get('result', ''), '○')
                with st.expander(f'{mark}  {r["criterion"]} {r["name"]} · Level {r["level"]} · {status}'):
                    _criterion(s, r, 'all_')
    ui.footer()
