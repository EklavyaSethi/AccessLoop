"""Agent mode: one button, the agent repairs the page inside the policy you set, and hands back what only you can decide."""
from __future__ import annotations
import streamlit as st
from .. import ui
from .review import _inputs

PHASE = {'perceive': ('Perceive', 'info'), 'plan': ('Plan', 'info'), 'gate': ('Policy check', 'neutral'),
         'act': ('Act', 'neutral'), 'commit': ('Verified', 'ok'), 'rollback': ('Rolled back', 'bad'),
         'escalate': ('Your turn', 'warn'), 'stop': ('Done', 'info'), 'verify': ('Verify', 'neutral')}


def _row(s: dict) -> str:
    label, tone = PHASE.get(s['phase'], (s['phase'], 'neutral'))
    rule = f' <code>{ui.esc(s["rule"])}</code>' if s.get('rule') else ''
    count = f'<span class="al-tl-n">{s["violations"]} left</span>' if s.get('violations') is not None and s['phase'] in ('commit', 'rollback', 'perceive') else ''
    detail = f'<div class="al-tl-d">{ui.esc(s["detail"])}</div>' if s.get('detail') else ''
    return (f'<li class="al-tl-{ui.esc(s["phase"])}">{ui.badge(label, tone)} <b>{ui.esc(s["title"])}</b>{rule} {count}'
            f'{detail}</li>')


TONE = {'commit': 'ok', 'rollback': 'bad', 'escalate': 'warn', 'stop': 'info', 'perceive': 'info', 'policy': 'dim'}


def _console(lines: list, running: bool = False) -> str:
    rows = ''.join(f'<div class="al-term-l {TONE.get(ph, "")}"><span class="t">{t:7.2f}s</span> <span class="p">{ui.esc(ph)}</span> '
                   f'{ui.esc(text)}</div>' for t, ph, text in lines)
    cursor = '<div class="al-term-l"><span class="cur" aria-hidden="true">▍</span></div>' if running else ''
    return (f'<div class="al-term" role="log" aria-label="Agent console" tabindex="0"><div class="al-term-h" aria-hidden="true">'
            f'<span></span><span></span><span></span> accessloop agent</div>{rows}{cursor}</div>')


def _timeline(steps: list[dict]) -> str:
    rows = ''.join(_row(s) for s in steps)
    return f'<ol class="al-tl" aria-label="Agent steps">{rows}</ol>'


def _value(s, state) -> None:
    """Measured agent time next to the same work by hand, with every assumption visible and editable."""
    from accessloop import roi
    value = state.get('roi')
    if not value:
        return
    e, a = value['estimate'], value['assumptions']
    c = a['currency']
    st.markdown('**Value of this run** ' + ui.badge('estimate', 'info'), unsafe_allow_html=True)
    ui.metrics([('Work by hand (estimate)', f'{e["minutes_by_hand"]:g} min', ''),
                ('Person\'s time with AccessLoop', f'{e["minutes_with_accessloop"]:g} min', 'good'),
                ('Saved on this page', f'{e["percent_saved"]}% · {roi.money(e["cost_saved"], c)}', 'good'),
                (f'Per year, {a["pages_per_year"]} pages like this', f'{e["hours_saved_per_year"]:,} h · {roi.money(e["cost_saved_per_year"], c)}', 'good')])
    st.caption(roi.summary(value) + ' ' + value['basis'])
    with st.expander('Change the assumptions (use your organisation\'s own figures)', icon=':material/tune:'):
        cols = st.columns(5)
        new = {}
        for col, key, step in zip(cols, ('minutes_by_hand', 'minutes_to_check', 'minutes_to_answer', 'cost_per_hour',
                                         'pages_per_year'), (1.0, 0.5, 0.5, 100.0, 10)):
            label = roi.LABELS[key] + (f' ({c})' if key == 'cost_per_hour' else '')
            if key == 'pages_per_year':
                new[key] = col.number_input(label, min_value=1, max_value=100000, value=int(a[key]), step=int(step), key=f'roi_{key}')
            else:
                new[key] = col.number_input(label, min_value=0.0, max_value=100000.0, value=float(a[key]), step=step, key=f'roi_{key}')
        b1, b2, _ = st.columns([2, 2, 4])
        if b1.button('Recalculate', key='roi_apply'):
            s.set_roi(new)
            st.rerun()
        if b2.button('Back to the defaults', key='roi_reset'):
            s.set_roi({})
            for key in roi.LABELS:
                st.session_state.pop(f'roi_{key}', None)
            st.rerun()
        st.caption('Measured figures come from this run. The minutes and cost are assumptions: replace them with your '
                   'own. The run report shows the same figures, labelled as measured, assumed or estimated.')


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Agent mode', 'Set the rules once and let the agent repair the page. It scans, applies only the fixes '
                   'your policy allows, re-scans after every change, undoes anything that does not help, and stops to '
                   'ask you for anything that needs words only a person knows.', None, state)
    ui.need_loaded(state)
    ui.show_flash()

    ui.h2('1 · What the agent may do on its own')
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        level = st.radio('Fixes it may apply without asking', ['Low-risk only (recommended)', 'Low and medium risk'],
                         key='agent_risk', help='Low risk: adds or links information already on the page. Medium risk: '
                         'changes structure or behaviour, such as roles, tab order or heading levels.')
    limit = c2.number_input('Most changes in one run', min_value=1, max_value=400, value=200, step=10, key='agent_limit')
    c3.markdown('<div class="al-note">Never types text for you.<br>Stops after 6 rollbacks in a row.<br>'
                'Original file never touched.</div>', unsafe_allow_html=True)
    risks = ['low'] if level.startswith('Low-risk') else ['low', 'medium']
    st.markdown(f'<div class="al-note">{ui.ai_status_html()}</div>', unsafe_allow_html=True)
    from accessloop.ai_advisor import provider as _prov
    prov = _prov()
    use_ai = st.checkbox('Draft the words the agent needs (alt text, names, titles) for me to review'
                         + (' with AI' if prov != 'off' else ''), value=True, key='agent_ai',
                         help='Nothing is applied until you accept or edit each draft. Every draft and how you used it is recorded.')
    consent = False
    if use_ai and prov != 'off':
        consent = st.checkbox(f'I agree to send redacted snippets of this page to the AI ({"Google Gemini" if prov == "gemini" else "a model on this computer"}). '
                              'Field values, long numbers and e-mail addresses are removed first.', key='agent_ai_consent')
    elif use_ai:
        st.caption('AI is switched off, so drafts come from the page itself (file names, field names, the main heading) and are '
                   'labelled "no AI". Switch on Gemini in "AI assistant" in the sidebar.')
    auth = state.get('auth') or {}
    if auth.get('four_eyes'):
        st.info('Four-eyes mode is on. Starting the agent counts as the second approval, so only a signed-in approver can start it.')

    ui.h2('2 · Run')
    slow = st.checkbox('Presentation pace: pause briefly after each step so people can follow (the times shown stay real)',
                       value=True, key='agent_pace')
    named = ui.require_name(state, 'run the agent')
    if named:
        who = (auth.get('user') or {}).get('display') or ui.reviewer()
        st.caption(f'This run will be recorded as approved by {who}. Stay on this page until the console says "stop": '
                   'with AI drafting on, the last step can take up to 25 seconds.')
    if st.button(ui.t('Let the agent repair this page'), type='primary', key='agent_go', disabled=not named) and named:
        left, right = st.columns([5, 6])
        live = left.empty()
        term = right.empty()
        seen: list[dict] = []
        lines: list = []

        def on_step(step, run):
            seen.append(step.__dict__.copy())
            live.markdown(_timeline(seen), unsafe_allow_html=True)

        def on_log(line, run):
            lines.append(line)
            term.markdown(_console(lines[-40:], running=True), unsafe_allow_html=True)
        reviewer = ui.reviewer() or ((auth.get('user') or {}).get('display', ''))
        if ui.run(s.run_agent, risks, limit, reviewer, ui.language(), (), on_step, on_log, 0.35 if slow else 0,
                  ai_drafts=use_ai, ai_consent=consent):
            st.rerun()

    run = state.get('agent')
    if not run:
        st.caption('Nothing has run yet. The agent records its policy and every step in the signed audit log.')
        ui.footer()
        return

    ui.h2('3 · What happened')
    ui.metrics([('Violation nodes at first scan', run['before'], ''), ('Violation nodes now', run['after'], 'good' if run['after'] < run['before'] else ''),
                ('Fixes kept', run['applied'], 'good'), ('Rolled back', run['rolled_back'], 'bad' if run['rolled_back'] else ''),
                ('Waiting for you', len(run['questions']) + len(run['held']), '')])
    st.caption(f'Policy: {run["policy_text"]} Took {run["seconds"]} s.' + (f' {run["stopped"]}' if run.get('stopped') else ''))
    _value(s, state)
    d1, d2, _ = st.columns([2, 2, 3])
    for col, kind, label in ((d1, 'agent-html', 'Download agent run report'), (d2, 'agent-json', 'Download run record (JSON)')):
        try:
            content, fname, mime = s.export(kind)
            col.download_button(label, content, file_name=fname, mime=mime.split(';')[0], key=f'dl_{kind}',
                                type='primary' if kind == 'agent-html' else 'secondary')
        except Exception as error:  # noqa: BLE001
            col.caption(str(error))
    left, right = st.columns([5, 6])
    with left:
        with st.expander(f'Every step ({len(run["steps"])})', expanded=False):
            st.markdown(_timeline(run['steps']), unsafe_allow_html=True)
    with right:
        st.markdown(_console(run.get('console', [])), unsafe_allow_html=True)

    proposals = {(p['rule'], p['selector'], p['line']): p for p in state.get('proposals', [])}
    questions = [q for q in run['questions'] if (q['rule'], q['selector'], q['line']) in proposals]
    if questions:
        ui.h2('4 · The agent needs your words')
        st.caption('These fixes need text only a person knows. Fill in the ones you can; each answer is applied, re-scanned '
                   'and kept only if it verifies.')
        drafts = state.get('ai_drafts', {})
        if not drafts:
            if st.button('Draft these answers for me', key='agent_draft_now', disabled=not named):
                if ui.run(s.draft_answers, bool(st.session_state.get('agent_ai_consent')), ui.reviewer()):
                    st.rerun()
        answers = []
        for q in questions[:20]:
            p = proposals[(q['rule'], q['selector'], q['line'])]
            d = drafts.get(f'{q["rule"]}|{q["selector"]}|{q["line"]}')
            with st.container(border=True):
                st.markdown(f'**{ui.esc(p["title"])}** · line {p.get("line") or "?"} · `{ui.esc(p["selector"])}`')
                st.caption(p['explanation'])
                with st.expander('Where is this on the page?', icon=':material/my_location:'):
                    ui.where_is_it(s, p['id'], 'q_' + p['id'])
                if d:
                    for i, f in enumerate(p.get('fields', [])):
                        key = f'val_{p["id"]}_{i}'
                        if f['name'] in d and key not in st.session_state:
                            st.session_state[key] = d[f['name']]
                    who = f'AI draft · {d.get("_model", "")}' if d.get('_source') == 'ai' else 'Suggestion from the page (no AI)'
                    st.markdown(f'{ui.badge(who, "info" if d.get("_source") == "ai" else "neutral")}'
                                f'{ui.badge(d.get("_confidence", "low") + " confidence", "neutral")} '
                                f'<span style="color:#4a5568">{ui.esc(d.get("_why", ""))} Check it before applying.</span>',
                                unsafe_allow_html=True)
                values = _inputs(p) or {}
                if any(v for v in values.values()):
                    answers.append({'rule': q['rule'], 'selector': q['selector'], 'line': q['line'], 'values': values})
        if len(questions) > 20:
            st.caption(f'{len(questions) - 20} more are on the Review page.')
        if st.button(ui.t('Apply my answers'), type='primary', key='agent_answers', disabled=not answers or not named):
            if ui.run(s.answer, answers, ui.language(), ui.reviewer()):
                ui.flash('success', f'{len(answers)} answer(s) applied and re-verified. See the Review page for each result.')
                st.rerun()
    held = [h for h in run['held'] if (h['rule'], h['selector'], h['line']) in proposals]
    if held:
        ui.h2('Held for your approval')
        st.caption('The policy did not allow these. Review them one by one, or run the agent again with medium risk allowed.')
        st.dataframe([{'Rule': h['rule'], 'Element': h['selector'], 'Line': h['line'], 'Why it was held': h['why']} for h in held],
                     hide_index=True, **ui.stretch(st.dataframe))
    a, b, c = st.columns(3)
    with a:
        ui.link('review', 'Review the rest by hand', ':material/rule:')
    with b:
        ui.link('trace', 'Open the agent trace', ':material/timeline:')
    with c:
        ui.link('reports', 'Download the evidence', ':material/description:')
    ui.footer()
