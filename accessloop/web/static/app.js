'use strict';
(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const IMPACTS = ['critical', 'serious', 'moderate', 'minor'];
  const HANDLING = {
    live: 'Auto-fix now', auto: 'Planned · deterministic', assisted: 'Planned · reviewer input',
    guided: 'Guidance only', excluded: 'Not scanned',
  };
  const MAX_BYTES = 2 * 1024 * 1024;
  let state = { loaded: false, scanned: false, languages: [] };
  let catalog = null;

  /* ---------- helpers ---------- */
  function h(tag, props, ...kids) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === 'class') el.className = value;
      else if (key === 'text') el.textContent = value;
      else if (key.startsWith('on')) el.addEventListener(key.slice(2), value);
      else el.setAttribute(key, value === true ? '' : value);
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }
  const sr = (text) => h('span', { class: 'sr-only', text });
  const when = (ts) => String(ts || '').replace('T', ' ').replace('+00:00', ' UTC');
  const clear = (el) => { while (el.firstChild) el.removeChild(el.firstChild); };

  function announce(message) {
    const live = $('#live');
    live.textContent = '';
    requestAnimationFrame(() => { live.textContent = message; });
  }
  function showError(message) {
    const box = $('#alert');
    box.textContent = message;
    box.hidden = false;
  }
  function clearError() { $('#alert').hidden = true; }

  async function api(path, body) {
    const options = body === undefined ? {} : {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    };
    let response;
    try { response = await fetch(path, options); }
    catch (error) { throw new Error('Cannot reach the AccessLoop server. Is it still running?'); }
    let data = null;
    try { data = await response.json(); } catch (error) { /* not JSON */ }
    if (!response.ok) throw new Error((data && data.error) || `Request failed (${response.status}).`);
    return data;
  }

  async function run(button, action, after) {
    clearError();
    let ok = false;
    const buttons = [...document.querySelectorAll('.btn')].filter((b) => !b.disabled);
    if (button) button.setAttribute('aria-busy', 'true');
    buttons.forEach((b) => { b.disabled = true; });
    try { await action(); ok = true; }
    catch (error) { showError(error.message); }
    finally {
      buttons.forEach((b) => { if (b.isConnected) b.disabled = false; });
      if (button) button.removeAttribute('aria-busy');
      render();
      if (ok && after) after();
    }
  }

  /* ---------- rendering ---------- */
  function renderStepper() {
    const m = state.metrics;
    let current = 0;
    if (state.loaded) current = 1;
    if (state.scanned) current = m.eligible > 0 ? 2 : 4;
    const names = ['Load', 'Scan', 'Review', 'Verify', 'Report'];
    const list = $('#stepper');
    clear(list);
    names.forEach((name, index) => {
      const status = index < current ? 'done' : index === current ? 'current' : 'todo';
      const item = h('li', { 'data-state': status, 'aria-current': status === 'current' ? 'step' : null },
        h('span', { class: 'num', 'aria-hidden': 'true', text: status === 'done' ? '✓' : String(index + 1) }),
        h('span', { text: name }),
        status === 'done' ? sr(' (done)') : null);
      list.append(item);
    });
  }

  function renderLanguages() {
    const select = $('#language');
    if (select.options.length !== state.languages.length && state.languages.length) {
      const previous = select.value || 'en';
      clear(select);
      state.languages.forEach((lang) => select.append(h('option', { value: lang.code, text: `${lang.name} (${lang.code})` })));
      select.value = previous;
    }
    if (state.language) select.value = state.language;
  }

  function metricCard(value, label, delta) {
    return h('div', { class: 'metric' },
      h('div', { class: 'n' }, String(value), delta || null),
      h('div', { class: 'l', text: label }));
  }

  function renderResults() {
    const m = state.metrics;
    const metrics = $('#metrics');
    clear(metrics);
    const diff = m.current - m.baseline;
    let delta = null;
    if (diff !== 0) {
      delta = h('span', { class: `d ${diff < 0 ? 'good' : 'worse'}` },
        diff < 0 ? `▼ ${Math.abs(diff)}` : `▲ ${diff}`, sr(diff < 0 ? ' fewer than at first scan' : ' more than at first scan'));
    }
    metrics.append(
      metricCard(m.baseline, 'Detected at first scan'),
      metricCard(m.current, 'Detected now', delta),
      metricCard(m.eligible, 'Fixes ready for review'),
      metricCard(m.verified, `Verified fixes · ${m.rejected} rejected · ${m.rolled_back} rolled back`));

    const body = $('#sev-table tbody');
    clear(body);
    const keys = [...IMPACTS];
    if (state.severity.baseline.unknown || state.severity.current.unknown) keys.push('unknown');
    keys.forEach((key) => body.append(h('tr', null,
      h('td', null, h('span', { class: 'badge', 'data-sev': key, text: key })),
      h('td', { text: String(state.severity.baseline[key] || 0) }),
      h('td', { text: String(state.severity.current[key] || 0) }))));

    const outcome = $('#outcome');
    if (state.outcome) {
      const o = state.outcome;
      const text = o.status === 'verified' ? `Verified: ${o.rule} on ${o.selector}. ${o.detail}`
        : o.status === 'rejected' ? `Rejected: ${o.rule} on ${o.selector}. No change was written to the page.`
          : o.status === 'pending' ? `Waiting for a second reviewer: ${o.rule} on ${o.selector}. ${o.detail}`
          : `Rolled back: ${o.rule} on ${o.selector}. ${o.detail} The page is unchanged.`;
      outcome.dataset.kind = o.status;
      const heard = (o.announce_before || o.announce_after)
        ? ` Screen reader: ${o.announce_before || '–'} → ${o.announce_after || '–'}.` : '';
      outcome.textContent = text + heard;
      outcome.hidden = false;
    } else {
      outcome.hidden = true;
    }
    renderProposals();
    renderManual();
  }

  function diffBlock(lines) {
    const kinds = { add: ['+', 'Added: '], del: ['−', 'Removed: '], ctx: [' ', ''], meta: ['', ''] };
    return h('div', { class: 'diff', role: 'group', 'aria-label': 'Proposed change' },
      lines.filter((l) => l.kind !== 'meta').map((l) => h('div', { class: `line ${l.kind}` },
        h('span', { class: 'mark', 'aria-hidden': 'true', text: kinds[l.kind][0] }),
        kinds[l.kind][1] ? sr(kinds[l.kind][1]) : null,
        l.text)));
  }

  const previews = {};      // proposal id -> last preview message (kept across re-renders)
  const typedCache = {};    // proposal id -> {field: value} so typed text survives a re-render
  // Reviewer-typed text for fixes that need words only a person can supply. Nothing is guessed.
  function fieldControls(p) {
    if (!p.needs_input) return { node: null, read: () => null };
    const inputs = {};
    const rows = p.fields.map((f, i) => {
      const id = `f-${p.id}-${i}`;
      let control;
      if (f.kind === 'select') {
        control = h('select', { id, name: f.name }, (f.options || []).map(([value, label]) => h('option', { value, text: label })));
      } else if (f.kind === 'checkbox') {
        control = h('input', { id, name: f.name, type: 'checkbox' });
      } else {
        control = h('input', { id, name: f.name, type: 'text', maxlength: String(f.max || 150), autocomplete: 'off' });
      }
      const cache = (typedCache[p.id] = typedCache[p.id] || {});
      if (cache[f.name] !== undefined) {
        if (f.kind === 'checkbox') control.checked = !!cache[f.name]; else control.value = cache[f.name];
      }
      control.addEventListener(f.kind === 'text' ? 'input' : 'change',
        () => { cache[f.name] = f.kind === 'checkbox' ? control.checked : control.value; });
      inputs[f.name] = { control, kind: f.kind };
      const hint = f.help ? h('span', { class: 'hint', id: `${id}-h`, text: f.help }) : null;
      if (hint) control.setAttribute('aria-describedby', `${id}-h`);
      return h('div', { class: 'field' }, h('label', { for: id, text: f.label }), control, hint);
    });
    return {
      node: h('div', { class: 'typed-fields', role: 'group', 'aria-label': 'Text only you can supply' }, rows),
      read: () => Object.fromEntries(Object.entries(inputs).map(([k, v]) =>
        [k, v.kind === 'checkbox' ? v.control.checked : v.control.value])),
    };
  }

  function renderProposals() {
    const box = $('#proposals');
    clear(box);
    $('#ai-btn').disabled = state.proposals.length === 0;
    if (!state.proposals.length) {
      box.append(h('p', { class: 'empty', text: 'No fixes are waiting for review in the current scan.' }));
      return;
    }
    if ((state.batches || []).length) {
      box.append(h('div', { class: 'batch-bar', role: 'group', 'aria-label': 'Approve similar fixes together' },
        h('p', { class: 'hint', text: 'Approve similar automatic fixes together. One re-scan; the batch is kept only if every fix works.' }),
        state.batches.slice(0, 8).map((b) => h('button', { type: 'button', class: 'btn', onclick: (e) => approveBatch(b, e.currentTarget) },
          `Approve all ${b.count}: ${b.title}`))));
    }
    state.proposals.forEach((p) => {
      const ref = `${p.rule} on ${p.selector}`;
      const typed = fieldControls(p);
      const card = h('article', { class: 'proposal', 'data-sev': p.impact, 'aria-label': `Proposed fix: ${ref}` },
        h('div', { class: 'proposal-head' },
          h('h3', { text: p.title }),
          h('span', { class: 'badge', 'data-sev': p.impact, text: p.impact }),
          p.kind === 'review' ? h('span', { class: 'badge', text: 'axe needs review' }) : null,
          p.needs_input ? h('span', { class: 'badge', text: 'you type the text' }) : null,
          p.risk === 'medium' ? h('span', { class: 'badge', text: 'check the result' }) : null,
          h('code', { class: 'sel', text: p.selector }),
          h('span', { class: 'hint', text: `${p.line ? `line ${p.line} · ` : ''}${p.rule}${p.wcag.length ? ` · WCAG ${p.wcag.join(', ')} · Level ${p.level}` : ''}` })),
        h('p', { text: p.explanation }),
        h('p', { class: 'evidence', text: `Evidence: ${p.evidence}` }),
        p.ai ? h('p', { class: 'ai-note', text: `AI advice: ${p.ai.verdict.toUpperCase()}. ${p.ai.reason}` }) : null,
        diffBlock(p.diff),
        typed.node,
        previews[p.id] ? h('p', { class: 'preview-note', role: 'status', text: previews[p.id] }) : null,
        h('div', { class: 'actions' },
          h('button', { type: 'button', class: 'btn btn-primary', onclick: (e) => approve(p, e.currentTarget, typed.read()) },
            'Approve and verify', sr(` fix for ${ref}`)),
          h('button', { type: 'button', class: 'btn', onclick: (e) => previewFix(p, e.currentTarget, typed.read()) },
            'Preview screen reader', sr(` for ${ref}`)),
          h('button', { type: 'button', class: 'btn', onclick: (e) => reject(p, e.currentTarget) },
            'Reject (no change)', sr(` for ${ref}`))));
      box.append(card);
    });
  }

  function externalLink(url, label) {
    return h('a', { href: url, target: '_blank', rel: 'noopener noreferrer' }, label, sr(' (opens in a new tab)'));
  }

  function renderManual() {
    const box = $('#manual');
    clear(box);
    if (!state.unresolved.length) {
      box.append(h('p', { class: 'empty', text: 'Nothing is waiting for manual review in this scan.' }));
    } else {
      const rows = state.unresolved.map((u) => h('tr', null,
        h('td', null, h('span', { class: 'badge', 'data-sev': u.impact, text: u.impact })),
        h('td', null, h('code', { text: u.rule }), h('div', { class: 'hint', text: u.wcag.length ? `WCAG ${u.wcag.join(', ')} · ${u.level}` : 'Best practice' })),
        h('td', null, h('code', { text: u.selector })),
        h('td', null, u.help, u.description ? h('div', { class: 'hint', text: u.description }) : null),
        h('td', null, h('span', { class: 'badge', 'data-h': u.handling, text: u.handling_label }),
          u.help_url ? h('div', null, externalLink(u.help_url, 'How to fix')) : null)));
      box.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
        h('caption', { class: 'sr-only', text: 'Findings that need manual review' }),
        h('thead', null, h('tr', null, ['Severity', 'Rule', 'Element', 'Issue', 'AccessLoop handling'].map((t) => h('th', { scope: 'col', text: t })))),
        h('tbody', null, rows))));
    }
    const note = $('#incomplete');
    note.hidden = !state.metrics.incomplete;
    note.textContent = state.metrics.incomplete
      ? `${state.metrics.incomplete} axe rule(s) were inconclusive and need a manual check.` : '';
  }

  function renderPreview() {
    const grid = $('#preview-grid');
    $('#preview-empty').hidden = state.loaded;
    grid.hidden = !state.loaded;
    if (!state.loaded) return;
    const original = `/preview/original.html?v=${state.sha_original.slice(0, 10)}`;
    const working = `/preview/working.html?v=${state.sha_current.slice(0, 10)}`;
    const a = $('#frame-original'), b = $('#frame-working');
    if (a.getAttribute('src') !== original) a.setAttribute('src', original);
    if (b.getAttribute('src') !== working) b.setAttribute('src', working);
  }

  function renderAudit() {
    const box = $('#audit');
    clear(box);
    if (!state.loaded) { box.append(h('p', { class: 'empty', text: 'Nothing recorded yet. Load a page to begin.' })); return; }
    const fixes = (state.changes || []).filter((c) => c.kind === 'fix');
    if (fixes.length) {
      box.append(h('h3', { text: 'Undo one fix' }),
        h('p', { class: 'hint', text: 'Undo a single earlier fix and keep the others. Refused if anything else would get worse.' }),
        h('ul', { class: 'stack' }, fixes.map((c) => h('li', null, `${c.rule} on ${c.selector} (${c.label})`,
          c.status === 'reverted' ? ' – undone' : h('button', { type: 'button', class: 'btn btn-quiet', onclick: (e) => run(e.currentTarget, async () => {
            applyState(await api('/api/revert', { n: c.n, reviewer: reviewer() }));
            announce(state.outcome ? state.outcome.detail : 'Done.');
          }) }, 'Undo', sr(` ${c.rule} fix`))))));
    }
    box.append(h('h3', { text: 'Decisions' }));
    if (!state.fix_log.length) box.append(h('p', { class: 'hint', text: 'No fixes approved or rejected yet.' }));
    else box.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
      h('caption', { class: 'sr-only', text: 'Reviewer decisions' }),
      h('thead', null, h('tr', null, ['Time', 'Decision', 'Rule', 'Element', 'Result', 'Reviewer'].map((t) => h('th', { scope: 'col', text: t })))),
      h('tbody', null, [...state.fix_log].reverse().map((f) => h('tr', null,
        h('td', { text: when(f.time_utc) }), h('td', { text: f.decision }), h('td', null, h('code', { text: f.rule })),
        h('td', null, h('code', { text: f.selector })), h('td', { text: `${f.status.replace('_', ' ')}: ${f.detail}` }),
        h('td', { text: f.reviewer || 'not recorded' })))))));
    const a = state.audit || {};
    box.append(h('p', { class: a.verified ? 'ok-note' : 'bad-note', role: 'status' },
      h('strong', { text: `Audit log hash chain: ${a.verified ? 'verified' : 'FAILED'}. ` }),
      `${a.entries || 0} append-only entries; each stores the hash of the one before it. Head hash: `,
      h('code', { text: (a.head_sha256 || '-').slice(0, 24) })));
    box.append(h('h3', { text: 'Events and file fingerprints' }));
    box.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
      h('caption', { class: 'sr-only', text: 'Audit events' }),
      h('thead', null, h('tr', null, ['Time', 'Event', 'Detail', 'Working file SHA-256'].map((t) => h('th', { scope: 'col', text: t })))),
      h('tbody', null, state.events.map((e) => h('tr', null,
        h('td', { text: when(e.timestamp_utc) }), h('td', { text: e.event }), h('td', { text: e.detail }),
        h('td', null, h('code', { text: (e.working_sha256 || '').slice(0, 16) }))))))));
  }

  function downloadCard(title, text, href, enabled, opts = {}) {
    const control = enabled
      ? h('a', { class: 'btn is-link', href, target: opts.newTab ? '_blank' : null, rel: opts.newTab ? 'noopener noreferrer' : null },
        opts.label || 'Download', opts.newTab ? sr(' (opens in a new tab)') : null, sr(` ${title}`))
      : h('button', { type: 'button', class: 'btn', disabled: true }, opts.label || 'Download', sr(` ${title} (not available yet)`));
    return h('div', { class: 'dl' }, h('h3', { text: title }), h('p', { text }), control);
  }

  function renderReports() {
    $('#reports-note').textContent = state.scanned
      ? 'These reflect the current session. To save the evidence report as a PDF, open it and use your browser’s Print command.'
      : 'Run a scan to enable the session reports. The issue catalogue is always available.';
    const grid = $('#dl-grid');
    clear(grid);
    grid.append(
      downloadCard('Evidence report', 'Printable remediation report: summary, each fix with its diff and reviewer, remaining issues, limits and audit trail.', '/api/report.html', state.scanned, { newTab: true, label: 'Open report' }),
      downloadCard('Evidence data (JSON)', 'The same record in machine-readable form, with file fingerprints.', '/api/report.json', state.scanned),
      downloadCard('Repaired HTML', 'The working copy with every approved fix applied.', '/api/working.html', state.loaded),
      downloadCard('Original HTML', 'Your untouched original for comparison.', '/api/original.html', state.loaded),
      downloadCard('Code change (git patch)', 'Apply the approved fixes to your repository with git am.', '/api/export/patch', state.loaded),
      downloadCard('Conformance report (VPAT-style)', 'All 55 WCAG 2.2 A and AA criteria with conformance levels.', '/api/export/acr', state.scanned, { newTab: true, label: 'Open report' }),
      downloadCard('Jira import (CSV)', 'One ticket per remaining issue.', '/api/export/jira', state.scanned),
      downloadCard('GitHub issues', 'Markdown plus a gh script that files one issue per remaining problem.', '/api/export/github', state.scanned),
      downloadCard('Test results (JUnit XML)', 'For CI dashboards.', '/api/export/junit', state.scanned),
      downloadCard('Issue catalogue (CSV)', 'Every axe rule with WCAG mapping and how AccessLoop handles it.', '/api/catalog.csv', true),
      downloadCard('Issue catalogue (Markdown)', 'The full catalogue including all 55 WCAG 2.2 A and AA criteria.', '/api/catalog.md', true));
  }

  /* ---------- coverage ---------- */
  function renderCoverage() {
    if (!catalog) return;
    const s = catalog.summary;
    const metrics = $('#cov-metrics');
    clear(metrics);
    metrics.append(
      metricCard(s.total_rules, 'axe rules in the engine'),
      metricCard(s.scanned_today, 'run by AccessLoop today'),
      metricCard(s.by_handling.live, 'with a live auto-fix'),
      metricCard(s.criteria_manual_only, `of ${s.criteria_total} WCAG criteria need a human check`));
    filterRules();
    const body = $('#crit-table tbody');
    clear(body);
    catalog.criteria.forEach((c) => body.append(h('tr', null,
      h('td', { text: c.criterion }), h('td', { text: c.name }), h('td', { text: c.level }),
      h('td', null, c.axe_rules.length ? c.axe_rules.map((r, i) => [i ? ', ' : '', h('code', { text: r })]) : h('strong', { text: 'none' })),
      h('td', { text: c.next_step.text }), h('td', { text: c.bfsi || '' }))));
  }

  function filterRules() {
    if (!catalog) return;
    const query = $('#cov-search').value.trim().toLowerCase();
    const kind = $('#cov-filter').value;
    const rows = catalog.rules.filter((r) => (!kind || r.handling === kind) && (!query
      || [r.rule_id, r.title, r.wcag.join(' '), r.note, r.level, HANDLING[r.handling]].join(' ').toLowerCase().includes(query)));
    const body = $('#cov-table tbody');
    clear(body);
    rows.forEach((r) => body.append(h('tr', null,
      h('td', null, h('code', { text: r.rule_id })), h('td', { text: r.wcag.join(', ') || '–' }), h('td', { text: r.level }),
      h('td', null, h('span', { class: 'badge', 'data-h': r.handling, text: HANDLING[r.handling] })),
      h('td', { text: r.priority || '–' }), h('td', { text: r.scanned_today ? 'yes' : 'no' }), h('td', { text: r.note }))));
    $('#cov-count').textContent = `Showing ${rows.length} of ${catalog.rules.length} rules.`;
  }

  /* ---------- main render ---------- */
  function renderAuth() {
    const auth = state.auth || {};
    $('#signin').hidden = !auth.required;
    $('#tablist').hidden = !!auth.required;
    document.querySelectorAll('[role="tabpanel"]').forEach((p) => { if (auth.required) p.hidden = true; });
    const who = $('#whoami');
    who.hidden = !auth.user;
    clear(who);
    if (auth.user) {
      who.append(`Signed in as ${auth.user.display} (${auth.user.role}); your decisions are signed. `,
        h('button', { type: 'button', class: 'btn btn-quiet', onclick: (e) => run(e.currentTarget, async () => applyState(await api('/api/logout', {}))) }, 'Sign out'));
      $('#reviewer').value = `${auth.user.display} (${auth.user.user})`;
      $('#reviewer').disabled = true;
    } else {
      $('#reviewer').disabled = false;
    }
    $('#four-eyes').checked = !!auth.four_eyes;
    const box = $('#pending');
    clear(box);
    (auth.pending || []).forEach((item) => {
      const field = auth.user ? null : h('input', { type: 'text', id: `cw-${item.id}`, 'aria-label': 'Confirming reviewer (a different person)', placeholder: 'Confirming reviewer' });
      box.append(h('div', { class: 'preview-note', role: 'group', 'aria-label': 'Waiting for confirmation' },
        `Waiting for confirmation: ${item.rule} on ${item.selector}, approved by ${item.requested_by}. `, field,
        h('button', { type: 'button', class: 'btn btn-primary', onclick: (e) => run(e.currentTarget, async () => {
          applyState(await api('/api/confirm', { id: item.id, reviewer: field ? field.value : '' }));
          announce('Confirmed and applied.');
        }) }, 'Confirm and apply')));
    });
  }

  function render() {
    renderAuth();
    const pill = $('#file-pill');
    pill.hidden = !state.loaded;
    pill.textContent = state.loaded ? `File: ${state.source_name}` : '';
    $('#scan-btn').disabled = !state.loaded;
    $('#reset-btn').disabled = !state.loaded;
    if (state.reviewer && !$('#reviewer').value) $('#reviewer').value = state.reviewer;
    renderLanguages();
    renderStepper();
    $('#preload').hidden = !(state.loaded && !state.scanned);
    if (state.loaded && !state.scanned) $('#source-preview').textContent = state.source_preview || '';
    $('#results').hidden = !state.scanned;
    if (state.scanned) renderResults();
    renderPreview();
    renderAudit();
    renderReports();
  }

  /* ---------- actions ---------- */
  function applyState(next) { state = next; }
  const reviewer = () => $('#reviewer').value.trim();
  const language = () => $('#language').value;

  function loadSample(button) {
    return run(button, async () => {
      const id = $('#sample-select').value;
      if (!id) throw new Error('Choose a sample page first.');
      applyState(await api('/api/load', { sample: id, allow_scripts: $('#allow-scripts').checked }));
      announce(`Loaded ${state.source_name}. Run the accessibility scan next.`);
    });
  }

  function loadFile(file) {
    return run(null, async () => {
      if (!file) return;
      if (file.size > MAX_BYTES) throw new Error('That file is over 2 MB. AccessLoop accepts HTML files under 2 MB.');
      const html = await file.text();
      applyState(await api('/api/load', { name: file.name, html, allow_scripts: $('#allow-scripts').checked }));
      announce(`Loaded ${state.source_name}. Run the accessibility scan next.`);
    }).finally(() => { $('#file-input').value = ''; });
  }

  function scan(button) {
    return run(button, async () => {
      applyState(await api('/api/scan', { language: language(), best_practice: $('#best-practice').checked,
        extended: $('#extended').checked }));
      const m = state.metrics;
      announce(`Scan complete. ${m.baseline} violations found, ${m.eligible} fixes ready for review, ${m.manual} need manual review.`);
    }, () => {
      const heading = $('#h-summary');
      heading.setAttribute('tabindex', '-1');
      heading.focus();
    });
  }

  function decide(path, p, button, label, values) {
    return run(button, async () => {
      applyState(await api(path, { id: p.id, language: language(), reviewer: reviewer(), values }));
      announce(`${label} ${p.rule} on ${p.selector}.`);
    }, () => $('#outcome').focus());
  }
  const approve = (p, button, values) => decide('/api/approve', p, button, 'Approved and checked:', values);
  function previewFix(p, button, values) {
    return run(button, async () => {
      const res = await api('/api/preview', { id: p.id, language: language(), values });
      const v = res.preview;
      const msg = `Before: ${v.announce_before || '–'} → After: ${v.announce_after || '–'}. ` +
        (v.would_pass ? 'This change would pass verification.' : `This change would be rolled back: ${v.detail}`);
      previews[p.id] = msg;
      announce(msg);
    });
  }
  function approveBatch(b, button) {
    return run(button, async () => {
      applyState(await api('/api/approve-batch', { rule: b.rule, language: language(), reviewer: reviewer() }));
      announce(`Batch of ${b.count} ${b.rule} fixes: ${state.outcome ? state.outcome.status.replace('_', ' ') : 'done'}.`);
    }, () => $('#outcome').focus());
  }
  const reject = (p, button) => decide('/api/reject', p, button, 'Rejected, no change made:');

  function reset(button) {
    return run(button, async () => {
      applyState(await api('/api/reset', {}));
      announce('Reset to the original page.');
    });
  }

  function askAi(button) {
    return run(button, async () => {
      const result = await api('/api/ai-review', { consent: $('#ai-consent').checked });
      applyState(result.state);
      announce(result.message);
      $('#ai-status').textContent = result.message;
      $('#ai-status').hidden = false;
    });
  }

  /* ---------- tabs ---------- */
  function initTabs() {
    const tabs = [...document.querySelectorAll('[role="tab"]')];
    function select(tab, focus) {
      tabs.forEach((t) => {
        const active = t === tab;
        t.setAttribute('aria-selected', String(active));
        t.tabIndex = active ? 0 : -1;
        document.getElementById(t.getAttribute('aria-controls')).hidden = !active;
      });
      if (focus) tab.focus();
    }
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => select(tab, false));
      tab.addEventListener('keydown', (event) => {
        const keys = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 };
        if (!(event.key in keys)) return;
        event.preventDefault();
        select(tabs[(keys[event.key] + tabs.length) % tabs.length], true);
      });
    });
  }

  /* ---------- start ---------- */
  async function init() {
    initTabs();
    $('#load-sample').addEventListener('click', (e) => loadSample(e.currentTarget));
    $('#file-input').addEventListener('change', (e) => loadFile(e.target.files[0]));
    $('#scan-btn').addEventListener('click', (e) => scan(e.currentTarget));
    $('#reset-btn').addEventListener('click', (e) => reset(e.currentTarget));
    $('#ai-btn').addEventListener('click', (e) => askAi(e.currentTarget));
    $('#shots-btn').addEventListener('click', () => {
      const v = Date.now();
      $('#shot-original').src = `/api/screenshot/original.png?v=${v}`;
      $('#shot-working').src = `/api/screenshot/working.png?v=${v}`;
      $('#shots').hidden = false;
      announce('Rendering both versions.');
    });
    $('#login-btn').addEventListener('click', (e) => run(e.currentTarget, async () => {
      applyState(await api('/api/login', { user: $('#login-user').value, password: $('#login-pass').value }));
      $('#login-pass').value = '';
      announce('Signed in.');
    }));
    $('#four-eyes').addEventListener('change', (e) => run(null, async () => applyState(await api('/api/four-eyes', { on: e.target.checked }))));
    $('#cov-search').addEventListener('input', filterRules);
    $('#cov-filter').addEventListener('change', filterRules);
    try {
      const [samples, current, cat] = await Promise.all([api('/api/samples'), api('/api/state'), api('/api/catalog')]);
      const select = $('#sample-select');
      samples.samples.forEach((s) => select.append(h('option', { value: s.id, text: `${s.label} (${s.id.replace('examples/', '')})` })));
      catalog = cat;
      applyState(current);
      renderCoverage();
    } catch (error) {
      showError(error.message);
    }
    render();
  }
  init();
})();
