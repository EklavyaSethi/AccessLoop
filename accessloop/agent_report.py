"""Agent run report: one file with everything the agent did on a page, for an auditor or a regulator.

Contents: who approved the policy and what it allowed; page fingerprints before and after; the full step-by-step
console; every change with its exact before/after text and re-scan result; rollbacks; what was handed to a person
(questions, held fixes) and how AI-drafted answers were used; the audit-log entries of the run with their hashes and
signatures, and whether the whole hash chain still verifies. Two forms: JSON (machine-readable) and a standalone HTML
page that prints to PDF. The JSON's own SHA-256 is printed in the HTML so the two can be matched.
"""
from __future__ import annotations
import hashlib
import json
from html import escape as e

from .web.report import CSS, _table

RUN_EVENTS = ('agent_started', 'verified', 'rolled_back', 'refused', 'agent_finished', 'ai_drafted', 'ai_draft_decision',
              'scanned')


def build(state: dict) -> dict:
    """Machine-readable report from a session state (Session.state())."""
    run = state.get('agent')
    if not run:
        raise ValueError('The agent has not run on this page yet.')
    events = list(reversed(state.get('events', [])))          # state lists newest first
    start = max((i for i, ev in enumerate(events) if ev['event'] == 'agent_started'), default=0)
    run_events = [ev for ev in events[start:] if ev['event'] in RUN_EVENTS]
    changes = [f for f in state.get('fix_log', []) if f.get('decision', '').startswith('approved')]
    doc = {
        'report': 'AccessLoop agent run report', 'accessloop_version': run.get('version'),
        'page': run.get('page') or state.get('source_name'),
        'approved_by': run.get('approved_by'), 'started_utc': run.get('started_utc'), 'finished_utc': run.get('finished_utc'),
        'policy': {**run['policy'], 'text': run.get('policy_text')},
        'fingerprints': {'original_sha256': state.get('sha_original'), 'before_run_sha256': run.get('sha_before'),
                         'after_run_sha256': run.get('sha_after'), 'current_sha256': state.get('sha_current')},
        'summary': {k: run[k] for k in ('before', 'after', 'reviews_before', 'reviews_after', 'applied', 'decisions',
                                         'rolled_back', 'seconds', 'stopped')} | {
            'questions_for_a_person': len(run.get('questions', [])), 'held_for_approval': len(run.get('held', [])),
            'answer_drafts': run.get('drafts', 0)},
        'console': [{'t': t, 'phase': ph, 'text': text} for t, ph, text in run.get('console', [])],
        'changes': [{k: f.get(k) for k in ('time_utc', 'rule', 'wcag', 'level', 'selector', 'where', 'decision', 'status', 'detail',
                                           'reviewer', 'before', 'after')} for f in changes],
        'handed_to_a_person': {'questions': run.get('questions', []), 'held': run.get('held', [])},
        'audit': {**(state.get('audit') or {}),
                  'run_entries': [{k: ev.get(k) for k in ('timestamp_utc', 'event', 'detail', 'reviewer', 'working_sha256',
                                                         'hash', 'prev_hash', 'signer') if ev.get(k) is not None}
                                  | ({'signed': True} if ev.get('sig') else {}) for ev in run_events]},
        'limits': 'Automated checks cover part of WCAG. A clean scan is not a conformance claim; see the manual checklist.',
    }
    return doc


def state_from_run(engine, run, page: str, approved_by: str, started_utc: str, sha_before: str) -> dict:
    """The parts of a session state that build() needs, for runs outside the app (command line)."""
    from .planner import sha256
    from .workflow import read_source
    d = run.to_dict()
    d.update({'page': page, 'approved_by': approved_by, 'started_utc': started_utc, 'sha_before': sha_before,
              'sha_after': sha256(engine.current_html), 'version': __import__('accessloop').__version__, 'drafts': 0})
    log = []
    for st in run.steps:
        if st.phase in ('commit', 'rollback'):
            ch = st.changes or []
            log.append({'time_utc': None, 'rule': st.rule, 'wcag': [], 'level': '',
                        'selector': ', '.join(c['selector'] for c in ch), 'decision': 'approved by agent policy',
                        'status': 'verified' if st.phase == 'commit' else 'rolled_back', 'detail': st.detail,
                        'reviewer': approved_by, 'before': '\n'.join(c['before'] for c in ch),
                        'after': '\n'.join(c['after'] for c in ch)})
    return {'agent': d, 'events': list(reversed(engine.events)), 'fix_log': log, 'source_name': page,
            'sha_original': sha256(read_source(engine.workspace / 'original.html')),
            'sha_current': sha256(engine.current_html), 'audit': engine.audit_status()}


def to_json(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False)


def to_html(doc: dict) -> str:
    raw = to_json(doc)
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    s, pol, fp, audit = doc['summary'], doc['policy'], doc['fingerprints'], doc['audit']
    cards = ''.join(f'<div class="card"><div class="n">{e(str(n))}</div><div class="l">{e(l)}</div></div>' for n, l in (
        (f'{s["before"]} → {s["after"]}', 'violation nodes'), (s['applied'], 'fixes kept'), (s['rolled_back'], 'rolled back'),
        (s['questions_for_a_person'] + s['held_for_approval'], 'handed to a person')))
    console = '\n'.join(f'{c["t"]:7.2f}s  {c["phase"]:<9} {c["text"]}' for c in doc['console'])
    change_rows = [[e((c['time_utc'] or '').replace('T', ' ').replace('+00:00', ' UTC')),
                    f'<code>{e(c["rule"])}</code><br><span class="muted">WCAG {e(", ".join(c.get("wcag") or []) or "best practice")}</span>',
                    f'<code>{e(c["selector"] or "")}</code>' + (f'<br><span class="muted">{e(c["where"])}</span>' if c.get('where') else ''),
                    f'<pre class="del">{e(c["before"] or "")}</pre><pre class="add">{e(c["after"] or "")}</pre>',
                    f'<span class="tag {"ok" if c["status"] == "verified" else "bad"}">{e(c["status"].replace("_", " "))}</span>'
                    f'<br><span class="muted">{e(c["decision"])}. {e(c["detail"] or "")}</span>']
                   for c in doc['changes']]
    q_rows = [[f'<code>{e(q["rule"])}</code>', e(str(q.get("line") or "")), f'<code>{e(q["selector"])}</code>',
               e(q.get('question', '')[:200])] for q in doc['handed_to_a_person']['questions']]
    h_rows = [[f'<code>{e(h["rule"])}</code>', e(str(h.get("line") or "")), f'<code>{e(h["selector"])}</code>', e(h['why'])]
              for h in doc['handed_to_a_person']['held']]
    a_rows = [[e((r.get('timestamp_utc') or '').replace('T', ' ').replace('+00:00', ' UTC')), e(r['event']), e(r.get('detail', '')),
               e(r.get('reviewer') or ''), f'<code class="hash">{e((r.get("hash") or "")[:16])}…</code>'
               + (' <span class="tag ok">signed</span>' if r.get('signed') else '')] for r in audit.get('run_entries', [])]
    chain = 'verified' if audit.get('verified') else 'FAILED'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AccessLoop agent run report</title><style>{CSS}
pre.console{{background:#0d1117;color:#d6deeb;padding:14px 16px;border-radius:10px;font-size:.78rem;line-height:1.5}}</style></head>
<body><main>
<header class="rep"><h1>Agent run report</h1>
<p>{e(doc['page'] or '')} · approved by {e(doc['approved_by'] or 'not recorded')} · {e((doc['started_utc'] or '').replace('T', ' ').replace('+00:00', ''))} UTC · AccessLoop {e(doc['accessloop_version'] or '')}</p></header>
<div class="cards">{cards}</div>
<div class="note">The agent applied only what the policy below allowed, re-scanned the page after every change, kept a change
only if its problem was gone and nothing else got worse, and undid it otherwise. It typed no text: fixes that need words were
handed to a person.</div>
<h2>Policy (approved by {e(doc['approved_by'] or 'not recorded')})</h2>
<p>{e(pol.get('text') or '')}</p>
<h2>Page fingerprints (SHA-256)</h2>
<table><tbody>
<tr><th scope="row">Original file (never modified)</th><td><code class="hash">{e(fp['original_sha256'] or '')}</code></td></tr>
<tr><th scope="row">Before this run</th><td><code class="hash">{e(fp['before_run_sha256'] or '')}</code></td></tr>
<tr><th scope="row">After this run</th><td><code class="hash">{e(fp['after_run_sha256'] or '')}</code></td></tr>
</tbody></table>
<h2>What the agent did, step by step</h2>
<pre class="console">{e(console)}</pre>
<h2>Changes ({len(doc['changes'])})</h2>
{_table(['Time', 'Rule', 'Elements', 'Exact change', 'Result'], change_rows, 'No changes were kept.')}
<h2>Handed to a person: fixes that need words ({len(q_rows)})</h2>
{_table(['Rule', 'Line', 'Element', 'What is needed'], q_rows, 'None.')}
<h2>Held for approval: outside the policy ({len(h_rows)})</h2>
{_table(['Rule', 'Line', 'Element', 'Why it was held'], h_rows, 'None.')}
<h2>Audit log entries for this run</h2>
<p>The full audit log has {audit.get('entries', 0)} entries; its hash chain is <strong>{chain}</strong>.
Head hash <code class="hash">{e(audit.get('head_sha256') or '-')}</code>. Check it any time with
<code>python -m accessloop audit verify audit.jsonl</code>.</p>
{_table(['Time', 'Event', 'Detail', 'By', 'Entry hash'], a_rows, 'No entries.')}
<h2>Limits</h2><p class="muted">{e(doc['limits'])}</p>
<p class="muted">SHA-256 of the matching JSON report: <code class="hash">{digest}</code></p>
</main></body></html>"""
