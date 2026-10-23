"""Printable remediation evidence report (standalone HTML, no scripts, prints cleanly to PDF)."""
from __future__ import annotations
from html import escape as e

IMPACTS = ('critical', 'serious', 'moderate', 'minor')

CSS = """
:root{--ink:#0f1b2d;--muted:#4a5870;--line:#d5dce8;--navy:#0b1f3a;--blue:#1747b8;--ok:#0e6b3a;--okbg:#e3f5eb;--bad:#9b1c1c;--badbg:#fde8e8;--bg:#f4f6fa}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:960px;margin:0 auto;padding:32px 24px 56px}
header.rep{background:var(--navy);color:#fff;border-radius:14px;padding:28px 30px;margin-bottom:24px}
header.rep h1{margin:0 0 6px;font-size:1.7rem;letter-spacing:-.02em}
header.rep p{margin:0;color:#cfd9ec}
h2{margin:34px 0 10px;font-size:1.2rem;letter-spacing:-.01em;border-bottom:2px solid var(--line);padding-bottom:6px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card .n{font-size:1.9rem;font-weight:750;letter-spacing:-.03em}
.card .l{color:var(--muted);font-size:.85rem}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:.9rem}
th,td{text-align:left;vertical-align:top;padding:9px 11px;border-bottom:1px solid var(--line)}
th{background:#eaeff8;font-weight:650}
code,pre{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:.82rem}
pre{margin:4px 0;padding:8px 10px;background:#f1f4fa;border-radius:8px;white-space:pre-wrap;word-break:break-word}
pre.del{background:var(--badbg);color:#7a1515}pre.add{background:var(--okbg);color:#0b4d29}
.tag{display:inline-block;padding:1px 8px;border-radius:99px;font-size:.78rem;font-weight:650;border:1px solid var(--line);background:#fff}
.ok{color:var(--ok)}.bad{color:var(--bad)}
.note{background:#fff;border-left:4px solid var(--blue);padding:12px 16px;border-radius:6px;margin:12px 0}
.muted{color:var(--muted)}
.hash{word-break:break-all}
@media print{body{background:#fff}main{padding:0}.card,table{break-inside:avoid}tr{break-inside:avoid}header.rep{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
@media (max-width:720px){.cards{grid-template-columns:repeat(2,1fr)}}
"""


def _table(headers: list[str], rows: list[list[str]], empty: str) -> str:
    if not rows:
        return f'<p class="muted">{e(empty)}</p>'
    head = ''.join(f'<th scope="col">{e(h)}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _audit_block(a: dict) -> str:
    if not a:
        return ''
    state = 'verified' if a.get('verified') else 'FAILED'
    return (f'<p>Audit log (<code>{e(a.get("file", ""))}</code>): {a.get("entries", 0)} entries, hash chain '
            f'<strong>{state}</strong>. {e(a.get("message", ""))}<br>Head hash: <code class="hash">{e(a.get("head_sha256") or "-")}</code></p>'
            '<p class="muted">Each audit entry contains the hash of the entry before it, so editing, deleting or reordering any '
            'entry is detected. Publish or sign the head hash to make the log tamper-evident to outside parties.</p>')


def build_html(d: dict) -> str:
    m = d['metrics']
    cov = d['coverage']
    fixes = d.get('fix_log', [])
    applied = [f for f in fixes if f['decision'].startswith('approved')]
    sev_rows = [[e(k.title()), str(d['severity']['baseline'].get(k, 0)), str(d['severity']['current'].get(k, 0))]
                for k in IMPACTS]
    fix_rows = []
    for f in fixes:
        status = f['status']
        cls = 'ok' if status == 'verified' else 'bad' if status == 'rolled_back' else ''
        fix_rows.append([
            e(f['time_utc'].replace('T', ' ').replace('+00:00', ' UTC')),
            f'<code>{e(f["rule"])}</code><br><span class="muted">WCAG {e(", ".join(f["wcag"]) or "n/a")}'
            f'{(" · Level " + e(f["level"])) if f["level"] else ""}</span>',
            f'<code>{e(f["selector"])}</code>',
            f'<pre class="del">{e(f["before"])}</pre><pre class="add">{e(f["after"])}</pre>'
            f'<span class="muted">{e(f["evidence"])}</span>'
            + (f'<br><span class="muted">Screen reader: {e(f.get("announce_before") or "–")} → {e(f.get("announce_after") or "–")}</span>'
               if f.get('announce_before') or f.get('announce_after') else ''),
            f'<span class="tag {cls}">{e(status.replace("_", " "))}</span><br><span class="muted">{e(f["detail"])}</span>',
            e(f['reviewer'] or 'not recorded'),
        ])
    open_rows = []
    for u in d['unresolved']:
        link = (f'<a href="{e(u["help_url"], quote=True)}" rel="noopener noreferrer">axe guidance</a>' if u['help_url'] else '')
        open_rows.append([
            f'<code>{e(u["rule"])}</code>', e(u['impact']), e(', '.join(u['wcag']) or 'best practice'),
            f'<code>{e(u["selector"])}</code>', f'{e(u["help"])}<br>{link}', e(u['handling_label']),
        ])
    event_rows = [[e(ev['timestamp_utc'].replace('T', ' ').replace('+00:00', ' UTC')), e(ev['event']), e(ev['detail']),
                   f'<code>{e((ev.get("working_sha256") or "")[:12])}</code>'] for ev in reversed(d['events'])]
    manual = ''.join(f'<li>{e(c["criterion"])} {e(c["name"])} (Level {e(c["level"])})</li>' for c in d['manual_only_criteria'])
    changed = 'The working copy differs from the original.' if d['changed'] else 'The working copy is identical to the original.'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AccessLoop remediation evidence report</title><style>{CSS}</style></head>
<body><main>
<header class="rep"><h1>Accessibility remediation evidence report</h1>
<p>{e(d['source_name'])} · generated {e(d['generated_utc'].replace('T', ' ').replace('+00:00', ' UTC'))} · AccessLoop {e(d['tool_version'])} · axe-core {e(d['axe_version'])}</p></header>

<h2>1. Summary</h2>
<div class="cards">
<div class="card"><div class="n">{m['baseline']}</div><div class="l">Violation nodes at first scan</div></div>
<div class="card"><div class="n">{m['current']}</div><div class="l">Violation nodes now</div></div>
<div class="card"><div class="n">{sum(1 for f in applied if f['status'] == 'verified')}</div><div class="l">Fixes approved and verified</div></div>
<div class="card"><div class="n">{m['manual']}</div><div class="l">Items left for manual review</div></div>
</div>
<p>{e(changed)} Reviewer recorded as typed in the tool: <strong>{e(d['reviewer'] or 'not recorded')}</strong>. The reviewer name is
not authenticated. Page language chosen by the reviewer: <code>{e(d['language'])}</code>.</p>

<h2>2. Severity before and after</h2>
{_table(['Severity', 'At first scan', 'Now'], sev_rows, '')}

<h2>3. Fixes and decisions</h2>
<p class="muted">Every source change was proposed from a fixed template, shown as a diff, and written only after the reviewer
approved it. Each write was followed by an independent re-scan; a change that did not improve the target rule or that raised any
other rule's count was rolled back automatically.</p>
{_table(['Time', 'Rule', 'Element', 'Change and evidence', 'Result', 'Reviewer'], fix_rows, 'No fixes were proposed for decision in this session.')}

<h2>4. Remaining issues (manual review queue)</h2>
{_table(['Rule', 'Severity', 'WCAG', 'Element', 'Issue', 'AccessLoop handling'], open_rows, 'No remaining automated findings.')}
{f'<p class="muted">{m["incomplete"]} axe rule(s) were inconclusive and need a manual check.</p>' if m['incomplete'] else ''}

<h2>5. What this report does and does not cover</h2>
<div class="note"><strong>Scope.</strong> Static HTML, checked by axe-core in headless Chromium against WCAG 2.0, 2.1 and 2.2 Level A and AA
rules{' plus axe best-practice rules' if m.get('best_practice') else ''}. AccessLoop runs {cov['scanned_today']} WCAG rules by default
(and {cov.get('best_practice_optional', 0)} more best-practice rules when that option is on) out of the {cov['total_rules']} rules in the engine. Of the {cov['criteria_total']} WCAG 2.2 A and AA
success criteria, {cov['criteria_manual_only']} cannot be tested by axe at all and still need a human check.</div>
<div class="note"><strong>Not a conformance certificate.</strong> A clean automated result does not show that a page is accessible. Keyboard,
screen-reader and human usability testing remain necessary, and this report does not replace an independent accessibility audit.</div>
<details><summary>Criteria that need a manual check ({cov['criteria_manual_only']})</summary><ul>{manual}</ul></details>

<h2>6. Audit trail</h2>
{_table(['Time', 'Event', 'Detail', 'Working file hash'], event_rows, 'No events recorded.')}

<h2>7. Sandbox: resources that did not load</h2>
<p class="muted">AccessLoop never fetches anything from the internet and never runs page scripts. These requests were refused
during the last scan, so anything they would have changed (styles, fonts, images, script-built content) was not part of it.</p>
{('<ul>' + ''.join(f'<li><code>{e(b)}</code></li>' for b in d.get('blocked', [])[:60]) + '</ul>') if d.get('blocked') else '<p>None: the page loaded completely.</p>'}
<p class="muted">Engine: {e((d.get('engine') or {}).get('axe', ''))} axe-core · {e((d.get('engine') or {}).get('browser', ''))}</p>

<h2>8. Integrity</h2>
<p>Original SHA-256: <code class="hash">{e(d['sha_original'])}</code><br>Current SHA-256: <code class="hash">{e(d['sha_current'])}</code></p>
{_audit_block(d.get('audit') or {})}
</main></body></html>"""
