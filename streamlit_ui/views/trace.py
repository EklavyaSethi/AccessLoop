"""Agent trace: the perceive → plan → human gate → act → verify → commit/rollback loop, step by step, with guardrails."""
from __future__ import annotations
import statistics
from collections import Counter

import streamlit as st
from .. import ui

STAGES = [
    ('Perceive', 'Sandboxed browser scan (axe-core). Nothing on the page can run.'),
    ('Plan', 'Each finding mapped to its exact source element; a fix drafted from a fixed template.'),
    ('Human gate', 'Nothing is written until a person approves. Text only a person knows is typed by them.'),
    ('Act', 'The patch is rebuilt server-side, checked against the file fingerprint, then written atomically.'),
    ('Verify', 'Full re-scan. The target rule must improve and no other rule may get worse.'),
    ('Commit / roll back', 'Verified changes stay; anything else is restored byte for byte.'),
]


def _when(ts: str) -> str:
    return ts.replace('T', ' ').replace('+00:00', '')[11:] if ts else ''


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Agent trace', 'Every step the agent took on this page, in order, with timings and the guardrails that '
                   'stopped or undid anything. This is the observability view of the loop.', None, None)
    ui.need_loaded(state)
    events = list(reversed(state['events']))           # oldest first
    scans = [e for e in events if e['event'] == 'scanned']
    applied = [e for e in events if e['event'] in ('verified', 'rolled_back')]
    verified = [e for e in events if e['event'] == 'verified']
    rolled = [e for e in events if e['event'] == 'rolled_back']
    rejected = [e for e in events if e['event'] == 'rejected']
    blocked = [e for e in events if e['event'] == 'blocked']
    proposals = sum(e.get('proposals', 0) for e in scans[:1])
    verify_ms = [e['verify_ms'] for e in applied if e.get('verify_ms') is not None]

    counts = [len(scans), proposals, len(applied) + len(rejected) + len(blocked), len(applied) + len(blocked),
              len(applied), f'{len(verified)} / {len(rolled)}']
    cells = ''.join(
        f'<div class="al-card" style="padding:14px 16px"><div class="al-ico" aria-hidden="true">{i + 1}</div>'
        f'<h3>{ui.esc(name)} <span style="float:right;color:var(--blue-dark)">{ui.esc(str(n))}</span></h3>'
        f'<p>{ui.esc(text)}</p></div>'
        for i, ((name, text), n) in enumerate(zip(STAGES, counts)))
    ui.h2('The agent loop')
    st.markdown(f'<div class="al-grid c3">{cells}</div>', unsafe_allow_html=True)
    st.caption('Numbers: scans run · fixes planned at first scan · human decisions · write attempts · changes re-verified · '
               'verified / rolled back.')

    ui.h2('Loop health')
    ui.metrics([
        ('Approved changes verified', f'{len(verified)} of {len(applied)}' if applied else '–', 'good' if applied and not rolled else ''),
        ('Automatic rollbacks', len(rolled), 'bad' if rolled else ''),
        ('Blocked by a guardrail', len(blocked), ''),
        ('Rejected by the reviewer', len(rejected), ''),
        ('Median time to verify', f'{statistics.median(verify_ms) / 1000:.1f} s' if verify_ms else '–', ''),
        ('Audit chain', 'Verified' if (state.get('audit') or {}).get('verified') else 'BROKEN',
         'good' if (state.get('audit') or {}).get('verified') else 'bad'),
    ])

    ui.h2('Guardrails that acted')
    guards = Counter(e.get('guardrail', 'other') for e in blocked + rolled)
    rows = [
        {'Guardrail': 'Input sandbox', 'What it does': 'Scripts, handlers, active URLs never run; no network; page cannot navigate away.',
         'Triggered': 'always on'},
        {'Guardrail': 'Human approval gate', 'What it does': 'No write without an explicit approval; rejections are recorded.',
         'Triggered': len(rejected)},
        {'Guardrail': 'Reviewer-text validation', 'What it does': 'Typed text must be present, short, and free of markup.',
         'Triggered': guards.get('reviewer-text validation', 0)},
        {'Guardrail': 'Stale-diff check', 'What it does': 'A fix made for an older version of the file is refused.',
         'Triggered': guards.get('stale-diff check', 0)},
        {'Guardrail': 'Patch re-validation', 'What it does': 'The patch is rebuilt server-side; anything that differs is refused.',
         'Triggered': guards.get('patch re-validation', 0)},
        {'Guardrail': 'Verification gate + rollback', 'What it does': 'Re-scan after every write; no improvement or any regression restores the file.',
         'Triggered': guards.get('verification gate', 0)},
    ]
    st.dataframe(rows, hide_index=True, **ui.stretch(st.dataframe))

    ui.h2('Step-by-step trace')
    stage_of = {'loaded': 'Perceive', 'reset': 'Perceive', 'scanned': 'Perceive + Plan', 'rejected': 'Human gate',
                'blocked': 'Guardrail', 'verified': 'Act + Verify → commit', 'rolled_back': 'Act + Verify → roll back'}
    trace = []
    for e in events:
        ms = e.get('verify_ms') or ((e.get('scan_ms') or 0) + (e.get('plan_ms') or 0)) or None
        trace.append({'#': e.get('seq'), 'Time (UTC)': _when(e.get('timestamp_utc', '')), 'Stage': stage_of.get(e['event'], e['event']),
                      'Rule': e.get('rule', ''), 'Reviewer': e.get('reviewer', ''),
                      'Duration': f'{ms / 1000:.2f} s' if ms else '', 'Detail': e.get('detail', '')[:160],
                      'Entry hash': (e.get('hash') or '')[:12]})
    st.dataframe(trace, hide_index=True, **ui.stretch(st.dataframe))

    if scans:
        first = scans[0]
        st.caption(f'First scan: {first.get("scan_ms", "?")} ms in the browser, {first.get("plan_ms", "?")} ms to plan '
                   f'{first.get("proposals", 0)} fixes ({first.get("input_proposals", 0)} need text from the reviewer).')
    with st.expander('Raw trace (JSON lines, as stored in audit.jsonl)'):
        st.json(events[-30:])
    ui.footer()
