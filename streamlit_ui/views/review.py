from __future__ import annotations
import streamlit as st
from .. import ui


def _banner(outcome: dict | None) -> None:
    if not outcome:
        return
    kind = outcome.get('status', '')
    text = {'verified': 'Verified', 'rejected': 'Rejected', 'rolled_back': 'Rolled back',
            'pending': 'Waiting for a second reviewer'}.get(kind, kind)
    detail = outcome.get('detail', '')
    heard = ''
    if outcome.get('announce_before') or outcome.get('announce_after'):
        heard = (f'<br><b>Screen reader:</b> {ui.esc(outcome.get("announce_before") or "–")} → '
                 f'{ui.esc(outcome.get("announce_after") or "–")}')
    st.markdown(f'<div class="al-banner {ui.esc(kind)}" role="status"><b>{ui.esc(text)}:</b> {ui.esc(detail)}{heard}</div>',
                unsafe_allow_html=True)


def _inputs(p: dict) -> dict | None:
    """Typed fields for fixes that need words only a person can supply. Nothing is guessed."""
    if not p.get('needs_input'):
        return None
    values: dict = {}
    for i, f in enumerate(p.get('fields', [])):
        key = f'val_{p["id"]}_{i}'
        if f.get('kind') == 'select':
            options = [(v, label) for v, label in f.get('options', [])]
            values[f['name']] = st.selectbox(f['label'], [v for v, _ in options], key=key,
                                             format_func=dict(options).get, help=f.get('help') or None)
        elif f.get('kind') == 'checkbox':
            values[f['name']] = st.checkbox(f['label'], key=key)
        elif f.get('kind') == 'textarea':
            values[f['name']] = st.text_area(f['label'], key=key, max_chars=f.get('max', 20000), height=160,
                                             placeholder=f.get('help') or None, help='Plain text only.')
        else:
            values[f['name']] = st.text_input(f['label'], key=key, max_chars=f.get('max', 150), help=f.get('help') or None)
    return values


def render() -> None:
    s = ui.session()
    state = s.state()
    ui.page_header('Review repair proposals', 'Nothing is written until you approve. Every fix comes from a fixed template, then the page is re-scanned and the change is undone automatically if anything gets worse.', 3, state)
    ui.need_scanned(state)
    ui.show_flash()
    _banner(state.get('outcome'))
    m = state['metrics']
    ui.metrics([('Waiting for your decision', m['eligible'], ''), ('Verified', m['verified'], 'good'),
                ('Rejected', m['rejected'], ''), ('Rolled back', m['rolled_back'], 'bad' if m['rolled_back'] else '')])
    named = ui.require_name(state, 'approve or reject fixes')

    proposals = state['proposals']
    if not proposals:
        st.success('No more fixes are waiting for review on this page.')
        a, b = st.columns(2)
        with a:
            ui.link('verify', 'See verification results', ':material/verified:')
        with b:
            ui.link('manual', 'Open manual review queue', ':material/assignment_late:')
        ui.footer()
        return

    with st.expander('Optional: ask AI to triage these proposals (off by default)'):
        ai = state.get('ai') or {}
        st.write('The AI only recommends approving or escalating. It never writes code and never decides the result.')
        st.info(ai.get('note', ''))
        consent = False
        if ai.get('provider', 'off') != 'off':
            consent = st.checkbox('I agree to send the redacted snippets of these proposed changes for this one review',
                                  key='ai_consent')
            with st.popover('See exactly what would be sent'):
                st.json(s.ai_preview())
        if st.button(ui.t('Request AI review'), key='ai_review', disabled=ai.get('provider', 'off') == 'off'):
            try:
                result = s.ai(consent)
            except Exception as error:  # noqa: BLE001
                result = {'available': False, 'message': str(error)}
            (st.success if result['available'] else st.warning)(result['message'])
            if result['available']:
                st.rerun()

    auth = state.get('auth') or {}
    with st.container(border=True):
        four = st.toggle('Four-eyes approval: a second person must confirm every fix before it is written',
                         value=auth.get('four_eyes', False), key='four_eyes_toggle')
        if four != auth.get('four_eyes', False):
            if ui.run(s.set_four_eyes, four):
                st.rerun()
        for item in auth.get('pending', []):
            st.markdown(f'**Waiting for confirmation:** {ui.esc(item["rule"])} on `{ui.esc(item["selector"])}` – approved by '
                        f'{ui.esc(item["requested_by"])} at {ui.esc(item["time_utc"])}', unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            who = '' if auth.get('user') else c1.text_input('Confirming reviewer (a different person)', key='confirm_who_' + item['id'])
            if c2.button(ui.t('Confirm and apply'), key='confirm_' + item['id'], type='primary', disabled=not named):
                with st.spinner('Applying and re-scanning…'):
                    if ui.run(s.confirm, item['id'], who):
                        st.rerun()

    batches = state.get('batches') or []
    if batches:
        with st.container(border=True):
            st.markdown('**Approve similar automatic fixes together**')
            st.caption('One approval, one re-scan. The batch is kept only if every one of the fixes works and nothing else '
                       'gets worse; otherwise the file is restored and you can approve them one at a time.')
            for b in batches[:8]:
                label = f'Approve all {b["count"]} “{b["title"]}” fixes'
                if st.button(label, key='batch_' + b['rule'], disabled=not named):
                    with st.spinner(f'Applying {b["count"]} fixes and re-scanning…'):
                        ok = ui.run(s.approve_batch, b['rule'], ui.language(), ui.reviewer())
                    if ok:
                        st.rerun()

    for p in proposals:
        with st.container(border=True):
            tags = ui.badge(p['impact'], p['impact']) + ui.badge(p['rule'], 'neutral')
            if p.get('kind') == 'review':
                tags += ui.badge('axe needs review', 'info')
            if p.get('needs_input'):
                tags += ui.badge('you type the text', 'info')
            if p.get('risk') == 'medium':
                tags += ui.badge('check the result', 'neutral')
            if p['wcag']:
                tags += ui.badge('WCAG ' + ', '.join(p['wcag']) + (f' · {p["level"]}' if p['level'] else ''), 'info')
            st.markdown(f'<div><b>{ui.esc(p["title"])}</b></div><div>{tags}</div>', unsafe_allow_html=True)
            st.write(p['explanation'])
            try:
                where = s.where(p['id'])['sentence']
            except Exception:  # noqa: BLE001
                where = ''
            if where:
                st.markdown(f'<div class="al-crumbs"><b>Where:</b> {ui.esc(where)}</div>', unsafe_allow_html=True)
            st.caption(f'Element: {p["selector"]}' + (f'  ·  line {p["line"]}' if p.get('line') else '') + f'  ·  Evidence: {p["evidence"]}')
            st.markdown(ui.diff_html(p['diff']), unsafe_allow_html=True)
            with st.expander('Where is this on the page? Code around it and a picture', icon=':material/my_location:'):
                ui.where_is_it(s, p['id'], p['id'])
            if p.get('ai'):
                st.info(f'AI advice: {str(p["ai"].get("verdict", "")).upper()}. {p["ai"].get("reason", "")}')
            values = _inputs(p)
            if st.button(ui.t('Preview what a screen reader will hear'), key='preview_' + p['id']):
                try:
                    pv = s.preview(p['id'], ui.language(), values)
                    (st.success if pv['would_pass'] else st.warning)(
                        f'Before: {pv["announce_before"] or "–"}  →  After: {pv["announce_after"] or "–"}. '
                        + ('This change would pass verification.' if pv['would_pass'] else f'This change would be rolled back: {pv["detail"]}'))
                except Exception as error:  # noqa: BLE001
                    st.error(str(error))
            a, b = st.columns(2)
            if a.button(ui.t('Approve and verify'), key='approve_' + p['id'], type='primary', disabled=not named):
                with st.spinner('Applying the change and re-scanning…'):
                    ok = ui.run(s.approve, p['id'], ui.language(), ui.reviewer(), values)
                if ok:
                    st.rerun()
            if b.button(ui.t('Reject (no change)'), key='reject_' + p['id'], disabled=not named):
                if ui.run(s.reject, p['id'], ui.reviewer()):
                    ui.flash('info', f'Rejected "{p["title"]}". Nothing was changed. The decision is in the audit log and the '
                                     'issue is now in the Manual review queue, where you can offer the fix again.')
                    st.rerun()
    ui.footer()
