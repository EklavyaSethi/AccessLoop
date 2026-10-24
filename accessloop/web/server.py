"""AccessLoop local web interface. Standard library only; bound to 127.0.0.1.

    python -m accessloop.web            # opens http://127.0.0.1:8765

The engine (workflow, planner, scanner, verifier) is unchanged. This module adds a JSON API,
a single in-memory working session, and a richer evidence log (who approved what, when).
"""
from __future__ import annotations
import argparse
import difflib
import json
import os
import re
import shutil
import time
import threading
import uuid
import webbrowser
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .. import __version__
from .. import catalog as catalog_mod
from ..ai_advisor import AIUnavailable, describe as ai_describe, payload_for, provider as ai_provider, review_proposals
from ..planner import sha256
from ..workflow import Workflow, WorkflowError, read_source
from . import report as report_mod
from .. import exports as exports_mod
from .. import manual_tests
from .. import accounts

PKG = Path(__file__).resolve().parent
STATIC = PKG / 'static'
ROOT = PKG.parent.parent
MAX_BODY = 3 * 1024 * 1024
IMPACTS = ('critical', 'serious', 'moderate', 'minor')
LANGUAGES = [
    ('en', 'English'), ('en-IN', 'English (India)'), ('hi', 'Hindi'), ('bn', 'Bengali'), ('ta', 'Tamil'),
    ('te', 'Telugu'), ('mr', 'Marathi'), ('gu', 'Gujarati'), ('kn', 'Kannada'), ('ml', 'Malayalam'),
    ('pa', 'Punjabi'), ('ur', 'Urdu'), ('fr', 'French'), ('es', 'Spanish'), ('de', 'German'),
]
LANGUAGE_CODES = {code for code, _ in LANGUAGES}
CONTENT_TYPES = {'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
                 '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml'}
APP_CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-src 'self'; "
           "base-uri 'none'; form-action 'none'; frame-ancestors 'self'; object-src 'none'")
PREVIEW_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox"


def cleanup_workspaces(base: Path, hours: float | None = None) -> int:
    """Delete workspace folders not touched for ACCESSLOOP_WORKSPACE_TTL_HOURS (default 24). Returns how many."""
    hours = float(os.getenv('ACCESSLOOP_WORKSPACE_TTL_HOURS', '24')) if hours is None else hours
    if not base.is_dir() or hours <= 0:
        return 0
    cutoff, removed = time.time() - hours * 3600, 0
    for owner in base.iterdir():
        for ws in (owner.iterdir() if owner.is_dir() else []):
            try:
                newest = max((f.stat().st_mtime for f in ws.rglob('*')), default=ws.stat().st_mtime) if ws.is_dir() else ws.stat().st_mtime
                if newest < cutoff:
                    shutil.rmtree(ws, ignore_errors=True) if ws.is_dir() else ws.unlink()
                    removed += 1
            except OSError:
                continue
    return removed


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _clean_name(value: object, limit: int = 80) -> str:
    text = re.sub(r'[\x00-\x1f\x7f]', '', str(value or '')).strip()
    return text[:limit]


def _clean_values(values: object) -> dict | None:
    """Typed values from a reviewer: short fields capped at 300 characters, captions text at 20,000."""
    if not isinstance(values, dict):
        return None
    out = {}
    for k, v in list(values.items())[:20]:
        key = str(k)[:40]
        out[key] = v if isinstance(v, bool) else str(v)[:20000 if key == 'cues' else 300]
    return out or None


def diff_lines(before: str, after: str) -> list[dict]:
    raw = list(difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile='before', tofile='proposed', n=2, lineterm=''))
    out = []
    for line in raw:
        if line.startswith(('---', '+++', '@@')):
            out.append({'kind': 'meta', 'text': line})
        elif line.startswith('+'):
            out.append({'kind': 'add', 'text': line[1:]})
        elif line.startswith('-'):
            out.append({'kind': 'del', 'text': line[1:]})
        else:
            out.append({'kind': 'ctx', 'text': line[1:] if line.startswith(' ') else line})
    if not any(x['kind'] in ('add', 'del') for x in out):
        out = [{'kind': 'del', 'text': before}, {'kind': 'add', 'text': after}]
    return out


class Session:
    """One working session: the engine plus the extra evidence the UI records."""

    def __init__(self, root: Path = ROOT):
        self.lock = threading.RLock()
        self.root = root
        self.identity = None            # accounts.Identity when signed in
        self.four_eyes = os.getenv('ACCESSLOOP_FOUR_EYES', '') == '1'
        self.pending: dict = {}         # proposal id / 'batch:<rule>' -> approval waiting for a second person
        cleanup_workspaces(root / '.accessloop_workspaces')
        self.catalog = catalog_mod.build()
        self.rules = {r['rule_id']: r for r in self.catalog['rules']}
        from ..scanner import CUSTOM_RULES
        for rid, info in CUSTOM_RULES.items():
            self.rules[rid] = {'rule_id': rid, 'title': info['title'], 'wcag': info['wcag'], 'level': info['level'],
                               'handling': 'live' if rid != 'al-forced-colors' else 'guided',
                               'note': 'AccessLoop browser check', 'help_url': ''}
        self.engine: Workflow | None = None
        self._clear()

    # ---- identity ---------------------------------------------------------------------------------
    def login(self, username: object, password: object) -> None:
        with self.lock:
            try:
                self.identity = accounts.login(str(username or ''), str(password or ''))
            except accounts.AccountError as error:
                raise ApiError(str(error), 401) from error
            self.reviewer = self.identity.label
            if self.engine is not None:
                self.engine.signer = self.identity

    def logout(self) -> None:
        with self.lock:
            self.identity = None      # pending approvals stay: a second person signs in to confirm them
            self.reviewer = ''
            if self.engine is not None:
                self.engine.signer = None

    def auth_required(self) -> bool:
        return accounts.enabled() and self.identity is None

    def _who(self, typed: object) -> str:
        """The reviewer recorded for a decision: the signed-in account when accounts are on, else the typed name."""
        if self.identity is not None:
            return self.identity.label
        if accounts.enabled():
            raise ApiError('Sign in first: decisions are recorded against a verified account.', 401)
        name = _clean_name(typed)
        if len(name) < 2 or not re.search(r'[^\W\d_]', name):
            raise ApiError('Enter your name first. Every decision and every agent run is recorded against the person who '
                           'made it.', 400)
        return name

    def set_four_eyes(self, on: object) -> None:
        with self.lock:
            if self.identity is not None and self.identity.role not in ('approver', 'admin') and not on:
                raise ApiError('Only an approver or admin can switch four-eyes approval off.', 403)
            self.four_eyes = bool(on)
            self.pending = {}
            if self.engine is not None and self.engine.loaded:
                self.engine._event('setting', f'Four-eyes approval {"on" if self.four_eyes else "off"}.',
                                   reviewer=self.reviewer or None)

    def _clear(self) -> None:
        self.source_name = ''
        self.language = 'en'
        self.reviewer = ''
        self.outcome: dict | None = None
        self.fix_log: list[dict] = []
        self.ai_review: dict = {}
        self.manual: dict = {}
        self.agent_run: dict | None = None
        self.ai_drafts: dict = {}           # 'rule|selector|line' -> draft (AI or rule-based) waiting for a person
        self.rejected: dict = {}            # (rule, selector, before) -> who rejected it and when: never offered again

    # ---- samples ------------------------------------------------------------------------------
    def samples(self) -> list[dict]:
        out = []
        for path in sorted((self.root / 'examples' / 'samples').rglob('*.html')):
            rel = path.relative_to(self.root).as_posix()
            match = re.search(r'<title>(.*?)</title>', path.read_text(encoding='utf-8', errors='replace'), re.I | re.S)
            out.append({'id': rel, 'label': (match.group(1).strip() if match else path.stem)})
        return out

    def _sample_text(self, sample_id: str) -> tuple[str, str]:
        allowed = {s['id'] for s in self.samples()}
        if sample_id not in allowed:
            raise ApiError('Unknown sample page.')
        return (self.root / sample_id).read_text(encoding='utf-8'), Path(sample_id).name

    # ---- actions ------------------------------------------------------------------------------
    def load(self, html: str | None, name: str, sample: str | None = None, allow_scripts: object = False) -> None:
        with self.lock:
            if sample:
                html, name = self._sample_text(sample)
            if not isinstance(html, str):
                raise ApiError('No HTML provided.')
            if self.auth_required():
                raise ApiError('Sign in first.', 401)
            owner = self.identity.user if self.identity is not None else 'local'
            engine = Workflow(self.root / '.accessloop_workspaces' / owner / uuid.uuid4().hex)
            engine.signer = self.identity
            # raises WorkflowError for unsafe or oversized input; the existing session is kept
            engine.load(html, allow_scripts=allow_scripts is True or allow_scripts == 'true')
            reviewer = self.reviewer
            self.engine = engine
            self._clear()
            self.pending = {}
            self.reviewer = reviewer
            self.source_name = _clean_name(name, 120) or 'uploaded.html'

    def _need_loaded(self) -> Workflow:
        if self.engine is None or not self.engine.loaded:
            raise ApiError('Load a page first.', 409)
        return self.engine

    def _need_scanned(self) -> Workflow:
        engine = self._need_loaded()
        if engine.current_scan is None:
            raise ApiError('Run a scan first.', 409)
        return engine

    @staticmethod
    def _language(value: object) -> str:
        if value not in LANGUAGE_CODES:
            raise ApiError('Choose a language from the list.')
        return str(value)

    def scan(self, language: object, best_practice: object = False, extended: object = False) -> None:
        with self.lock:
            engine = self._need_loaded()
            self.language = self._language(language)
            engine.scan(language=self.language, best_practice=bool(best_practice is True or best_practice == 'true'),
                        extended=bool(extended is True or extended == 'true'))
            self.outcome = None
            self.ai_review = {}

    def _proposal(self, engine: Workflow, proposal_id: object):
        match = next((p for p in engine.proposals if p.proposal_id == proposal_id), None)
        if match is None:
            raise ApiError('Unknown or expired proposal. Run the scan again.', 409)
        return match

    def _log(self, proposal, decision: str, status: str, detail: str, counts: tuple[int, int], who: str = '') -> None:
        info = self.rules.get(proposal.rule_id, {})
        outcome_ann = getattr(self, '_last_ann', ('', ''))
        self.fix_log.append({
            'announce_before': outcome_ann[0], 'announce_after': outcome_ann[1],
            'time_utc': _now(), 'proposal_id': proposal.proposal_id, 'rule': proposal.rule_id,
            'selector': proposal.selector, 'wcag': info.get('wcag', []), 'level': info.get('level', ''),
            'before': proposal.before, 'after': proposal.after, 'evidence': proposal.evidence,
            'explanation': proposal.explanation, 'decision': decision, 'status': status, 'detail': detail,
            'reviewer': who or self.reviewer, 'findings_before': counts[0], 'findings_after': counts[1],
        })

    def approve(self, proposal_id: object, language: object, reviewer: object, values: object = None) -> None:
        with self.lock:
            engine = self._need_scanned()
            proposal = self._proposal(engine, proposal_id)
            self.reviewer = self._who(reviewer)
            self.language = self._language(language)
            if values is not None and not isinstance(values, dict):
                raise ApiError('Typed values must be an object.')
            clean = _clean_values(values)
            if self.four_eyes:
                # Maker-checker: this approval only becomes a change when a different person confirms it.
                self.pending[proposal.proposal_id] = {'kind': 'single', 'values': clean, 'requested_by': self.reviewer,
                                                      'language': self.language, 'time_utc': _now(), 'rule': proposal.rule_id,
                                                      'selector': proposal.selector}
                engine._event('approval_requested', f'{proposal.proposal_id}: waiting for a second reviewer.',
                              proposal_id=proposal.proposal_id, rule=proposal.rule_id, reviewer=self.reviewer or None,
                              reviewer_text=clean)
                self.outcome = {'status': 'pending', 'detail': 'Approved by you; a second reviewer must confirm it.',
                                'rule': proposal.rule_id, 'selector': proposal.selector, 'before_count': 0, 'after_count': 0}
                return
            self._apply_now(engine, proposal, clean, self.reviewer)

    def confirm(self, proposal_id: object, reviewer: object) -> None:
        """Second person confirms a pending approval (four-eyes). The confirmer must differ from the requester."""
        with self.lock:
            engine = self._need_scanned()
            key = str(proposal_id)
            item = self.pending.get(key)
            if item is None:
                raise ApiError('Nothing is waiting for confirmation with that id.', 409)
            who = self._who(reviewer)
            if not who:
                raise ApiError('Enter the confirming reviewer\'s name.')
            if who.strip().lower() == item['requested_by'].strip().lower():
                raise ApiError('The person who approved a fix cannot also confirm it (four-eyes rule).', 403)
            if self.identity is not None and self.identity.role not in ('approver', 'admin'):
                raise ApiError('Only an approver or admin can confirm fixes.', 403)
            self.pending.pop(key)
            self.reviewer = who
            label = f'{item["requested_by"]} (approved) + {who} (confirmed)'
            if item['kind'] == 'batch':
                self._batch_now(engine, item['rule'], label)
            else:
                proposal = self._proposal(engine, key)
                self._apply_now(engine, proposal, item['values'], label)

    def _apply_now(self, engine: Workflow, proposal, clean: dict | None, label: str) -> None:
        from .. import context
        where = context.describe(engine.current_html, proposal.uid, proposal.edits)['sentence']
        out = engine.apply(proposal.proposal_id, approved=True, language=self.language, values=clean,
                           reviewer=label or None)
        self._last_ann = (out.announce_before, out.announce_after)
        applied = engine.last_candidate if out.status in ('verified', 'rolled_back') else None
        logged = proposal
        if applied is not None and applied.proposal_id == proposal.proposal_id:
            logged = applied      # records the exact text that was written, including reviewer-typed text
        self._log(logged, 'approved', out.status, out.detail, (out.before_count, out.after_count), label)
        self.fix_log[-1]['where'] = where
        self.outcome = {**out.to_dict(), 'rule': proposal.rule_id, 'selector': proposal.selector}
        self.ai_review = {}

    def where(self, proposal_id: object) -> dict:
        """Where a proposed fix sits on the page: plain sentence, breadcrumb and the surrounding source lines."""
        from .. import context
        with self.lock:
            engine = self._need_scanned()
            p = self._proposal(engine, proposal_id)
            return context.describe(engine.current_html, p.uid, p.edits)

    def picture(self, proposal_id: object) -> bytes | None:
        """A cropped picture of the element on the rendered page, outlined. None if it takes no space on screen."""
        from ..scanner import element_shot
        with self.lock:
            engine = self._need_scanned()
            p = self._proposal(engine, proposal_id)
            html, uid, assets = engine.current_html, p.uid, engine.assets_dir
        if uid is None:
            return None
        key = (sha256(html), uid)
        cache = self.__dict__.setdefault('_pictures', {})
        if key not in cache:
            if len(cache) > 60:
                cache.clear()
            cache[key] = element_shot(html, uid, assets)
        return cache[key]

    def preview(self, proposal_id: object, language: object, values: object = None) -> dict:
        with self.lock:
            engine = self._need_scanned()
            proposal = self._proposal(engine, proposal_id)
            if values is not None and not isinstance(values, dict):
                raise ApiError('Typed values must be an object.')
            clean = _clean_values(values)
            return engine.preview(proposal.proposal_id, language=self._language(language), values=clean)

    def approve_batch(self, rule: object, language: object, reviewer: object) -> None:
        with self.lock:
            engine = self._need_scanned()
            ids = [p.proposal_id for p in engine.proposals if p.rule_id == rule and not p.needs_input and not self._is_rejected(p)]
            if len(ids) < 2:
                raise ApiError('There is no batch of automatic fixes for that rule. Run the scan again.', 409)
            self.reviewer = self._who(reviewer)
            self.language = self._language(language)
            if self.four_eyes:
                self.pending[f'batch:{rule}'] = {'kind': 'batch', 'rule': rule, 'requested_by': self.reviewer, 'count': len(ids),
                                                 'time_utc': _now(), 'selector': f'{len(ids)} elements', 'values': None}
                engine._event('approval_requested', f'Batch of {len(ids)} {rule} fixes: waiting for a second reviewer.',
                              rule=str(rule), batch=ids, reviewer=self.reviewer or None)
                self.outcome = {'status': 'pending', 'detail': 'Batch approved by you; a second reviewer must confirm it.',
                                'rule': rule, 'selector': f'{len(ids)} elements', 'before_count': 0, 'after_count': 0}
                return
            self._batch_now(engine, rule, self.reviewer)

    def _batch_now(self, engine: Workflow, rule: object, label: str) -> None:
        ids = [p.proposal_id for p in engine.proposals if p.rule_id == rule and not p.needs_input and not self._is_rejected(p)]
        if len(ids) < 2:
            raise ApiError('That batch is no longer available. Run the scan again.', 409)
        first = next(p for p in engine.proposals if p.proposal_id == ids[0])
        out = engine.apply_batch(ids, language=self.language, reviewer=label or None)
        info = self.rules.get(first.rule_id, {})
        self.fix_log.append({
            'time_utc': _now(), 'proposal_id': f'batch of {len(ids)}', 'rule': first.rule_id,
            'selector': f'{len(ids)} elements', 'wcag': info.get('wcag', []), 'level': info.get('level', ''),
            'before': first.before, 'after': first.after + (f'  (+ {len(ids) - 1} similar)' if len(ids) > 1 else ''),
            'evidence': first.evidence, 'explanation': first.explanation, 'decision': 'approved (batch)',
            'status': out.status, 'detail': out.detail, 'reviewer': label,
            'findings_before': out.before_count, 'findings_after': out.after_count,
        })
        self.outcome = {**out.to_dict(), 'rule': first.rule_id, 'selector': f'{len(ids)} elements'}
        self.ai_review = {}

    # ---- agent mode -------------------------------------------------------------------------------
    def run_agent(self, risks: object = ('low',), max_changes: object = 200, reviewer: object = '', language: object = 'en',
                  deny_rules: object = (), on_step=None, on_log=None, pace: object = 0, ai_drafts: object = False,
                  ai_consent: object = False) -> dict:
        """Let the agent repair the page inside a policy. In four-eyes mode only an approver may start it: the policy is
        the second person's approval, given in advance."""
        from .. import agent
        with self.lock:
            engine = self._need_loaded()
            if engine.current_scan is None:
                engine.scan(language=self._language(language))
            levels = tuple(r for r in (risks or ()) if r in ('low', 'medium')) or ('low',)
            try:
                limit = max(1, min(int(max_changes), 400))
            except (TypeError, ValueError):
                raise ApiError('The change limit must be a number.') from None
            deny = tuple(str(r) for r in (deny_rules or ()) if str(r) in self.rules)
            self.reviewer = self._who(reviewer)
            if self.four_eyes and (self.identity is None or self.identity.role not in ('approver', 'admin')):
                raise ApiError('Four-eyes mode is on: only a signed-in approver can let the agent apply fixes.', 403)
            self.language = self._language(language)
            label = f'AccessLoop agent (policy approved by {self.reviewer})' if self.reviewer else 'AccessLoop agent'
            policy = agent.Policy(risks=levels, deny_rules=deny, max_changes=limit, skip=frozenset(self.rejected))

            def step(s, run):
                if s.phase in ('commit', 'rollback'):
                    info = self.rules.get(s.rule, {})
                    ch = s.changes or []
                    tag = (lambda c: f'line {c["line"]}: ' if len(ch) > 1 and c.get('line') else '')
                    self.fix_log.append({
                        'time_utc': _now(), 'proposal_id': f'agent step {s.n}', 'rule': s.rule,
                        'selector': ', '.join(c['selector'] for c in ch[:3]) + (f' (+{len(ch) - 3} more)' if len(ch) > 3 else '')
                                    or f'{s.size} element{"s" if s.size != 1 else ""}',
                        'wcag': info.get('wcag', []), 'level': info.get('level', ''),
                        'before': '\n'.join(tag(c) + c['before'] for c in ch),
                        'after': '\n'.join(tag(c) + c['after'] for c in ch),
                        'evidence': '', 'where': ' / '.join(dict.fromkeys(c.get('where', '') for c in ch if c.get('where')))[:400],
                        'explanation': info.get('title', s.rule), 'decision': 'approved by agent policy',
                        'status': 'verified' if s.phase == 'commit' else 'rolled_back', 'detail': s.detail,
                        'reviewer': label, 'findings_before': 0, 'findings_after': s.violations or 0})
                if on_step:
                    on_step(s, run)
            try:
                delay = max(0.0, min(float(pace or 0), 1.5))
            except (TypeError, ValueError):
                delay = 0.0
            started = _now()
            sha_before = sha256(engine.current_html)
            run = agent.run(engine, policy, reviewer=label, language=self.language, on_step=step, on_log=on_log, pace=delay)
            self.agent_run = run.to_dict()
            self.agent_run.update({'started_utc': started, 'finished_utc': _now(), 'approved_by': self.reviewer,
                                   'page': self.source_name, 'sha_before': sha_before, 'sha_after': sha256(engine.current_html),
                                   'version': __version__, 'drafts': 0})
            self.outcome = {'status': 'verified' if run.applied else 'unchanged',
                            'detail': f'Agent: {run.before} → {run.after} violations, {run.applied} fixes kept.',
                            'rule': 'agent', 'selector': '', 'before_count': run.before, 'after_count': run.after}
            self.ai_review = {}
            run_dict = self.agent_run
            proposals = tuple(engine.proposals)
        # The AI step talks to a remote model and can be slow: it runs WITHOUT the session lock, so every page of the
        # app stays usable meanwhile. Its results are stored under the lock when they arrive.
        if ai_drafts is True and run.questions:
            t0 = time.perf_counter()

            def say(phase, text):
                line = (round(run.seconds + time.perf_counter() - t0, 3), phase, text)
                run_dict['console'].append(line)
                if on_log:
                    on_log(line, run)
            self._draft(engine, ai_consent is True, say, proposals)
            with self.lock:
                run_dict['drafts'] = len(self.ai_drafts)
        return run_dict

    @staticmethod
    def _key(rule, selector, line) -> str:
        return f'{rule}|{selector}|{line}'

    def _draft(self, engine: Workflow, consent: bool, say=None, proposals=None) -> dict:
        """Call the drafter outside the session lock (it may wait on a remote model), then store results under it."""
        from .. import ai_drafts
        proposals = tuple(engine.proposals) if proposals is None else proposals
        drafts = ai_drafts.draft(engine, proposals, consent=consent, on_log=say)
        by_id = {p.proposal_id: p for p in proposals}
        with self.lock:
            for pid, d in drafts.items():
                p = by_id[pid]
                self.ai_drafts[self._key(p.rule_id, p.selector, p.line)] = d
        return drafts

    def draft_answers(self, consent: object = False, reviewer: object = '') -> dict:
        """Draft the words the agent asked for (AI when switched on and consented, else rule-based). Applies nothing."""
        with self.lock:
            engine = self._need_scanned()
            self.reviewer = self._who(reviewer)
            proposals = tuple(engine.proposals)
        lines: list = []
        self._draft(engine, consent is True, lambda phase, text: lines.append((0.0, phase, text)), proposals)
        with self.lock:
            if self.agent_run is not None:
                self.agent_run['console'] = list(self.agent_run.get('console', [])) + lines
                self.agent_run['drafts'] = len(self.ai_drafts)
            return dict(self.ai_drafts)

    def answer(self, answers: object, language: object, reviewer: object) -> list[dict]:
        """Apply the person's answers to the agent's questions. Each is matched to the current proposal by rule, element and
        line (ids change after every re-scan) and goes through the normal approval path (four-eyes, verify, rollback)."""
        if not isinstance(answers, list):
            raise ApiError('Answers must be a list.')
        results = []
        for a in answers[:100]:
            if not isinstance(a, dict) or not isinstance(a.get('values'), dict):
                continue
            with self.lock:
                engine = self._need_scanned()
                match = next((p for p in engine.proposals if p.rule_id == a.get('rule') and p.selector == a.get('selector')
                              and p.line == a.get('line') and p.needs_input), None)
            if match is None:
                results.append({'rule': a.get('rule'), 'status': 'gone', 'detail': 'No longer on the page.'})
                continue
            key = self._key(match.rule_id, match.selector, match.line)
            d = self.ai_drafts.get(key)
            try:
                self.approve(match.proposal_id, language, reviewer, a['values'])
                results.append({'rule': match.rule_id, 'status': (self.outcome or {}).get('status', ''),
                                'detail': (self.outcome or {}).get('detail', '')})
                if d:
                    typed = {k: str(v) for k, v in a['values'].items()}
                    drafted = {k: str(v) for k, v in d.items() if not k.startswith('_')}
                    use = 'accepted as drafted' if all(typed.get(k) == v for k, v in drafted.items()) else 'edited by the person'
                    src = 'AI draft' if d.get('_source') == 'ai' else 'rule-based suggestion'
                    with self.lock:
                        engine._event('ai_draft_decision', f'{match.rule_id}: {src} {use}; result {results[-1]["status"]}.',
                                      rule=match.rule_id, source=d.get('_source'), model=d.get('_model'), drafted=drafted,
                                      applied=typed, use=use, reviewer=self.reviewer)
                        if self.fix_log and self.fix_log[-1]['rule'] == match.rule_id:
                            self.fix_log[-1]['decision'] = f'approved ({src}, {use})'
                    self.ai_drafts.pop(key, None)
            except (ApiError, WorkflowError) as error:
                results.append({'rule': match.rule_id, 'status': 'refused', 'detail': str(error)})
        return results

    def revert(self, n: object, reviewer: object) -> None:
        with self.lock:
            engine = self._need_scanned()
            try:
                index = int(n)
            except (TypeError, ValueError) as error:
                raise ApiError('Choose a fix to undo.') from error
            self.reviewer = self._who(reviewer)
            target = next((c for c in engine.changes() if c['n'] == index), None)
            out = engine.revert(index, language=self.language, reviewer=self.reviewer or None)
            rule = target['rule'] if target else ''
            info = self.rules.get(rule, {})
            self.fix_log.append({'time_utc': _now(), 'proposal_id': f'undo #{index}', 'rule': rule,
                                 'selector': target['selector'] if target else '', 'wcag': info.get('wcag', []),
                                 'level': info.get('level', ''), 'before': '', 'after': '', 'evidence': '',
                                 'explanation': 'Reviewer undid an earlier fix.', 'decision': 'undone',
                                 'status': 'reverted' if out.status == 'verified' else 'refused', 'detail': out.detail,
                                 'reviewer': self.reviewer, 'findings_before': out.before_count,
                                 'findings_after': out.after_count})
            self.outcome = {**out.to_dict(), 'rule': rule, 'selector': target['selector'] if target else ''}

    def reject(self, proposal_id: object, reviewer: object) -> None:
        with self.lock:
            engine = self._need_scanned()
            proposal = self._proposal(engine, proposal_id)
            self.reviewer = self._who(reviewer)
            out = engine.reject(proposal.proposal_id, self.reviewer or None)
            self.rejected[(proposal.rule_id, proposal.selector, proposal.before)] = {'by': self.reviewer, 'time_utc': _now()}
            self._last_ann = ('', '')
            self._log(proposal, 'rejected', 'rejected', out.detail, (out.before_count, out.after_count))
            self.outcome = {**out.to_dict(), 'rule': proposal.rule_id, 'selector': proposal.selector}

    def unreject(self, rule: object, selector: object, reviewer: object) -> None:
        """Offer a rejected fix again (recorded)."""
        with self.lock:
            engine = self._need_scanned()
            self.reviewer = self._who(reviewer)
            keys = [k for k in self.rejected if k[0] == rule and k[1] == selector]
            for k in keys:
                self.rejected.pop(k)
            engine._event('setting', f'{rule} on {selector}: rejection withdrawn, the fix is offered again.',
                          rule=str(rule), selector=str(selector), reviewer=self.reviewer)

    def _is_rejected(self, p) -> bool:
        return (p.rule_id, p.selector, p.before) in self.rejected

    def reset(self) -> None:
        with self.lock:
            engine = self._need_loaded()
            engine.reset()
            reviewer, name, log, manual = self.reviewer, self.source_name, self.fix_log, self.manual
            self._clear()
            self.reviewer, self.source_name, self.manual = reviewer, name, manual
            # Decisions stay on record; the reset itself is recorded too (and in the hash-chained audit log).
            self.fix_log = log + [{'time_utc': _now(), 'proposal_id': '', 'rule': '(reset)', 'selector': '', 'wcag': [],
                                   'level': '', 'before': '', 'after': '', 'evidence': '', 'explanation': '',
                                   'decision': 'reset', 'status': 'reset',
                                   'detail': 'Working copy restored to the original; earlier fixes undone.',
                                   'reviewer': self.reviewer, 'findings_before': None, 'findings_after': None}]

    def ai_preview(self) -> list:
        """The exact (redacted) data an AI review would send."""
        with self.lock:
            return payload_for(self._need_scanned().proposals)

    def ai(self, consent: object = False) -> dict:
        with self.lock:
            engine = self._need_scanned()
            try:
                self.ai_review = review_proposals(engine.proposals, consent=consent is True)
            except AIUnavailable as error:
                return {'available': False, 'message': f'AI review unavailable; the deterministic workflow is unaffected. {error}'}
            return {'available': True, 'message': 'AI review completed. Its advice is non-binding.', 'advice': self.ai_review}

    # ---- views --------------------------------------------------------------------------------
    def state(self) -> dict:
        with self.lock:
            live = {p.proposal_id for p in self.engine.proposals} if self.engine is not None else set()
            self.pending = {k: v for k, v in self.pending.items() if k.startswith('batch:') or k in live}
            base = {'languages': [{'code': c, 'name': n} for c, n in LANGUAGES], 'version': __version__,
                    'reviewer': self.reviewer, 'loaded': False, 'scanned': False,
                    'auth': {'enabled': accounts.enabled(), 'required': self.auth_required(),
                             'user': ({'user': self.identity.user, 'display': self.identity.display,
                                       'role': self.identity.role} if self.identity else None),
                             'four_eyes': self.four_eyes,
                             'pending': [{'id': k, **{x: v[x] for x in ('kind', 'rule', 'selector', 'requested_by', 'time_utc')}}
                                         for k, v in self.pending.items()]}}
            engine = self.engine
            if engine is None or not engine.loaded:
                return base
            original = read_source(engine.workspace / 'original.html')
            current = engine.current_html
            base.update({'loaded': True, 'source_name': self.source_name, 'language': self.language,
                         'sha_original': sha256(original), 'sha_current': sha256(current),
                         'changed': original != current, 'outcome': self.outcome,
                         'events': list(reversed(engine.events)), 'fix_log': list(self.fix_log),
                         'audit': engine.audit_status(), 'manual_results': dict(self.manual), 'agent': self.agent_run,
                         'ai_drafts': dict(self.ai_drafts), 'ai_provider': ai_provider(),
                         'changes': [{k: c[k] for k in ('n', 'kind', 'rule', 'label', 'selector', 'status', 'reverts')}
                                     for c in engine.changes()]})
            scan = engine.current_scan
            if scan is None:
                base['source_preview'] = current[:6000]
                return base
            impact_of = {(f.rule_id, f.selector): f.impact for f in scan.items}
            proposals = []
            for p in engine.proposals:
                if self._is_rejected(p):
                    continue
                info = self.rules.get(p.rule_id, {})
                proposals.append({
                    'id': p.proposal_id, 'rule': p.rule_id, 'selector': p.selector,
                    'impact': impact_of.get((p.rule_id, p.selector), 'unknown'), 'title': info.get('title', p.rule_id),
                    'wcag': info.get('wcag', []), 'level': info.get('level', ''), 'explanation': p.explanation,
                    'evidence': p.evidence, 'diff': diff_lines(p.before, p.after), 'ai': self.ai_review.get(p.proposal_id),
                    'mode': p.mode, 'needs_input': p.needs_input, 'fields': list(p.fields), 'risk': p.risk,
                    'line': p.line, 'kind': scan.items[p.finding_index].kind if 0 <= p.finding_index < len(scan.items) else 'violation',
                })
            eligible = {(p.rule_id, p.selector) for p in engine.proposals if not self._is_rejected(p)}
            rejected_by = {(p.rule_id, p.selector): self.rejected[(p.rule_id, p.selector, p.before)]
                           for p in engine.proposals if self._is_rejected(p)}
            auto_by_rule: dict[str, int] = {}
            for p in engine.proposals:
                if not p.needs_input and not self._is_rejected(p):
                    auto_by_rule[p.rule_id] = auto_by_rule.get(p.rule_id, 0) + 1
            batches = [{'rule': r, 'count': n, 'title': self.rules.get(r, {}).get('title', r)}
                       for r, n in sorted(auto_by_rule.items(), key=lambda kv: -kv[1]) if n >= 2]
            unresolved = []
            for f in scan.items:
                if (f.rule_id, f.selector) in eligible:
                    continue
                info = self.rules.get(f.rule_id, {})
                unresolved.append({
                    'rule': f.rule_id, 'selector': f.selector, 'impact': f.impact, 'help': f.help,
                    'description': f.description[:600], 'wcag': info.get('wcag', []), 'level': info.get('level', ''),
                    'handling': info.get('handling', 'unclassified'),
                    'handling_label': (f'Fix rejected by {rejected_by[(f.rule_id, f.selector)]["by"]}: left unchanged for a person'
                                       if (f.rule_id, f.selector) in rejected_by else
                                       'Needs a human check (axe could not decide)' if f.kind == 'review'
                                       else catalog_mod.HANDLING.get(info.get('handling', ''), 'Unclassified')),
                    'rejected': (f.rule_id, f.selector) in rejected_by,
                    'note': info.get('note', ''), 'help_url': info.get('help_url', ''), 'kind': f.kind,
                })
            before = engine.before or scan
            events = engine.run_events
            base.update({
                'scanned': True, 'proposals': proposals, 'unresolved': unresolved, 'batches': batches,
                'blocked': list(scan.blocked), 'engine': scan.engine or {},
                'ai': {'provider': ai_provider(), 'note': ai_describe()},
                'metrics': {
                    'baseline': len(before.findings), 'current': len(scan.findings), 'eligible': len(proposals),
                    'manual': len(unresolved), 'incomplete': scan.incomplete, 'passed_rules': scan.passed_rules,
                    'needs_review': len(scan.reviews), 'best_practice': engine.best_practice,
                    'verified': sum(e['event'] == 'verified' for e in events),
                    'rejected': sum(e['event'] == 'rejected' for e in events),
                    'rolled_back': sum(e['event'] == 'rolled_back' for e in events),
                },
                'severity': {
                    'baseline': self._by_impact(before.findings), 'current': self._by_impact(scan.findings),
                },
                'rule_counts': {'baseline': dict(before.counts()), 'current': dict(scan.counts())},
            })
            return base

    @staticmethod
    def _by_impact(findings) -> dict:
        counts = Counter(f.impact for f in findings)
        out = {k: counts.get(k, 0) for k in IMPACTS}
        if counts.get('unknown'):
            out['unknown'] = counts['unknown']
        return out

    def report_payload(self) -> dict:
        with self.lock:
            self._need_scanned()
            state = self.state()
            return {
                **state, 'generated_utc': _now(), 'tool_version': __version__,
                'axe_version': self.catalog['axe_version'], 'coverage': self.catalog['summary'],
                'manual_only_criteria': [{'criterion': c['criterion'], 'name': c['name'], 'level': c['level']}
                                         for c in self.catalog['criteria'] if not c['axe_testable']],
            }

    def report_json(self) -> str:
        with self.lock:
            engine = self._need_scanned()
            doc = json.loads(engine.report_json())
            doc.update({'source_name': self.source_name, 'generated_utc': _now(), 'tool_version': __version__,
                        'axe_version': self.catalog['axe_version'], 'reviewer_recorded_as_typed': self.reviewer,
                        'language': self.language, 'fixes_and_decisions': self.fix_log,
                        'coverage': self.catalog['summary']})
            return json.dumps(doc, indent=2, ensure_ascii=False)

    # ---- manual checks ------------------------------------------------------------------------
    def record_manual(self, criterion: object, result: object, notes: object, reviewer: object) -> None:
        with self.lock:
            engine = self._need_loaded()
            known = {c['criterion'] for c in self.catalog['criteria']}
            if criterion not in known:
                raise ApiError('Unknown WCAG criterion.')
            if result not in {r for r, _ in manual_tests.RESULTS}:
                raise ApiError('Choose a result from the list.')
            self.reviewer = self._who(reviewer)
            note = re.sub(r'[\x00-\x1f\x7f]', ' ', str(notes or ''))[:500].strip()
            entry = {'result': result, 'notes': note, 'reviewer': self.reviewer, 'time_utc': _now()}
            if result:
                self.manual[str(criterion)] = entry
            else:
                self.manual.pop(str(criterion), None)
            engine._event('manual_check', f'{criterion}: {result or "cleared"}', criterion=str(criterion),
                          result=result or None, notes=note or None, reviewer=self.reviewer or None)

    def worksheet(self) -> list[dict]:
        with self.lock:
            return manual_tests.worksheet(self.catalog, self.manual)

    # ---- exports --------------------------------------------------------------------------------
    def export(self, kind: str) -> tuple[str, str, str]:
        """(content, file name, media type) for a standard export."""
        with self.lock:
            engine = self._need_loaded()
            base = re.sub(r'[^A-Za-z0-9_.-]+', '_', Path(self.source_name or 'page.html').stem) or 'page'
            if kind == 'evidence':
                doc = json.loads(self.report_json())
                if self.identity is not None:
                    doc = accounts.sign_document(doc, self.identity)
                return (json.dumps(doc, indent=2, ensure_ascii=False), f'{base}_evidence{"_signed" if self.identity else ""}.json',
                        'application/json; charset=utf-8')
            if kind in ('agent-html', 'agent-json'):
                from .. import agent_report
                try:
                    doc = agent_report.build(self.state())
                except ValueError as error:
                    raise ApiError(str(error), 409) from error
                if kind == 'agent-json':
                    if self.identity is not None:
                        doc = accounts.sign_document(doc, self.identity)
                    return agent_report.to_json(doc), f'{base}_agent_run{"_signed" if self.identity else ""}.json', \
                        'application/json; charset=utf-8'
                return agent_report.to_html(doc), f'{base}_agent_run_report.html', 'text/html; charset=utf-8'
            if kind == 'patch':
                text = exports_mod.git_patch(read_source(engine.workspace / 'original.html'), engine.current_html,
                                             self.source_name or 'index.html', self.reviewer, new_files=engine.extra_files())
                return text, f'{base}_accessloop.patch', 'text/x-diff; charset=utf-8'
            state = self.state()
            if not state.get('scanned'):
                raise ApiError('Run a scan first.', 409)
            if kind == 'acr':
                return (exports_mod.acr_html(state, self.catalog, self.manual), f'{base}_conformance_report.html',
                        'text/html; charset=utf-8')
            if kind == 'jira':
                return exports_mod.jira_csv(state), f'{base}_jira_issues.csv', 'text/csv; charset=utf-8'
            if kind == 'github':
                return exports_mod.github_issues(state), f'{base}_github_issues.md', 'text/markdown; charset=utf-8'
            if kind == 'junit':
                findings = [{'rule': u['rule'], 'kind': u.get('kind', 'violation'), 'impact': u['impact'], 'help': u['help'],
                             'selector': u['selector'], 'line': None} for u in state['unresolved']]
                findings += [{'rule': p['rule'], 'kind': p.get('kind', 'violation'), 'impact': p['impact'],
                              'help': p['title'], 'selector': p['selector'], 'line': p.get('line')} for p in state['proposals']]
                return (exports_mod.junit_xml([{'file': self.source_name, 'status': 'scanned', 'findings': findings}]),
                        f'{base}_junit.xml', 'application/xml; charset=utf-8')
            raise ApiError('Unknown export.', 404)

    def new_files(self) -> dict[str, str]:
        with self.lock:
            return self._need_loaded().extra_files()

    def bundle(self) -> bytes:
        """The repaired page plus every file the fixes created (captions ...), in their folders, as a zip."""
        import io
        import zipfile
        with self.lock:
            engine = self._need_loaded()
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
                z.writestr(self.source_name or 'index.html', engine.current_html)
                for name, text in engine.extra_files().items():
                    z.writestr(name, text)
            return buf.getvalue()

    def screenshots(self) -> tuple[bytes, bytes]:
        with self.lock:
            engine = self._need_loaded()
            key = sha256(engine.current_html)
            if getattr(self, '_shots', (None,))[0] != key:
                self._shots = (key, *engine.screenshots())
            return self._shots[1], self._shots[2]

    def file(self, which: str) -> str:
        with self.lock:
            engine = self._need_loaded()
            return read_source(engine.workspace / ('original.html' if which == 'original' else 'working.html'))


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'AccessLoop'

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    # ---- plumbing -----------------------------------------------------------------------------
    @property
    def session(self) -> Session:
        return self.server.session  # type: ignore[attr-defined]

    def _send(self, status: int, body: bytes, content_type: str, csp: str | None = APP_CSP, extra: dict | None = None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        if csp:
            self.send_header('Content-Security-Policy', csp)
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict, status: int = 200):
        self._send(status, json.dumps(payload, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def _text(self, text: str, content_type: str, filename: str | None = None, csp: str | None = APP_CSP):
        extra = {'Content-Disposition': f'attachment; filename="{filename}"'} if filename else None
        self._send(200, text.encode('utf-8'), content_type, csp, extra)

    def _guard(self) -> None:
        host = (self.headers.get('Host') or '').lower()
        if host not in self.server.allowed_hosts:  # type: ignore[attr-defined]
            raise ApiError('Host not allowed.', 403)

    def _body(self) -> dict:
        if (self.headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':
            raise ApiError('Content-Type must be application/json.', 415)
        origin = self.headers.get('Origin')
        if origin and origin.lower() != f'http://{self.headers.get("Host", "").lower()}':
            raise ApiError('Cross-origin request blocked.', 403)
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            raise ApiError('Bad Content-Length.')
        if length > MAX_BODY:
            raise ApiError('Request too large.', 413)
        try:
            data = json.loads(self.rfile.read(length) or b'{}')
        except json.JSONDecodeError:
            raise ApiError('Body is not valid JSON.')
        if not isinstance(data, dict):
            raise ApiError('Body must be a JSON object.')
        return data

    def _fail(self, error: Exception):
        if isinstance(error, ApiError):
            self._json({'error': str(error)}, error.status)
        elif isinstance(error, WorkflowError):
            self._json({'error': str(error)}, 400)
        else:
            self._json({'error': f'{type(error).__name__}: {error}'}, 500)

    # ---- routes -------------------------------------------------------------------------------
    def do_GET(self):
        try:
            self._guard()
            path = urlparse(self.path).path
            s = self.session
            if path == '/':
                return self._send(200, (STATIC / 'index.html').read_bytes(), CONTENT_TYPES['.html'])
            if path.startswith('/static/'):
                name = path[len('/static/'):]
                file = STATIC / name
                if '/' in name or '\\' in name or not file.is_file() or file.suffix not in CONTENT_TYPES:
                    raise ApiError('Not found.', 404)
                return self._send(200, file.read_bytes(), CONTENT_TYPES[file.suffix])
            if path == '/healthz':
                return self._json({'ok': True})
            if path == '/api/state':
                return self._json(s.state())
            if path == '/api/samples':
                return self._json({'samples': s.samples()})
            if path == '/api/catalog':
                return self._json(s.catalog)
            if path == '/api/catalog.csv':
                return self._text(catalog_mod.to_csv(s.catalog), 'text/csv; charset=utf-8', 'accessloop_issue_catalog.csv')
            if path == '/api/catalog.md':
                return self._text(catalog_mod.to_markdown(s.catalog), 'text/markdown; charset=utf-8', 'accessloop_issue_catalog.md')
            if path == '/api/report.html':
                return self._text(report_mod.build_html(s.report_payload()), CONTENT_TYPES['.html'], None,
                                  "default-src 'none'; style-src 'unsafe-inline'; img-src data:")
            if path in ('/api/screenshot/original.png', '/api/screenshot/working.png'):
                orig, work = s.screenshots()
                return self._send(200, orig if 'original' in path else work, 'image/png', None)
            if path.startswith('/api/export/'):
                content, name, ctype = s.export(path.rsplit('/', 1)[-1])
                return self._text(content, ctype, name, PREVIEW_CSP if 'html' in ctype else None)
            if path == '/api/worksheet':
                return self._json({'worksheet': s.worksheet()})
            if path == '/api/report.json':
                return self._text(s.report_json(), 'application/json; charset=utf-8', 'accessloop_evidence.json')
            if path in ('/api/working.html', '/api/original.html'):
                which = 'original' if 'original' in path else 'working'
                name = 'accessloop_original.html' if which == 'original' else 'accessloop_repaired.html'
                return self._text(s.file(which), CONTENT_TYPES['.html'], name, PREVIEW_CSP)
            if path in ('/preview/original.html', '/preview/working.html'):
                which = 'original' if 'original' in path else 'working'
                return self._text(s.file(which), CONTENT_TYPES['.html'], None, PREVIEW_CSP)
            raise ApiError('Not found.', 404)
        except Exception as error:  # noqa: BLE001 - every failure becomes a JSON error
            self._fail(error)

    def do_POST(self):
        try:
            self._guard()
            path = urlparse(self.path).path
            data = self._body()
            s = self.session
            if path == '/api/load':
                s.load(data.get('html'), _clean_name(data.get('name'), 120), data.get('sample'), data.get('allow_scripts', False))
            elif path == '/api/scan':
                s.scan(data.get('language', 'en'), data.get('best_practice', False), data.get('extended', False))
            elif path == '/api/approve':
                s.approve(data.get('id'), data.get('language', 'en'), data.get('reviewer'), data.get('values'))
            elif path == '/api/preview':
                return self._json({'preview': s.preview(data.get('id'), data.get('language', 'en'), data.get('values'))})
            elif path == '/api/login':
                s.login(data.get('user'), data.get('password'))
            elif path == '/api/logout':
                s.logout()
            elif path == '/api/four-eyes':
                s.set_four_eyes(data.get('on') is True)
            elif path == '/api/revert':
                s.revert(data.get('n'), data.get('reviewer'))
            elif path == '/api/confirm':
                s.confirm(data.get('id'), data.get('reviewer'))
            elif path == '/api/manual':
                s.record_manual(data.get('criterion'), data.get('result', ''), data.get('notes'), data.get('reviewer'))
            elif path == '/api/agent':
                s.run_agent(data.get('risks') or ['low'], data.get('max_changes', 200), data.get('reviewer'),
                            data.get('language', 'en'), data.get('deny_rules') or [], ai_drafts=data.get('ai_drafts') is True,
                            ai_consent=data.get('ai_consent') is True)
            elif path == '/api/draft':
                s.draft_answers(data.get('consent') is True, data.get('reviewer'))
            elif path == '/api/answer':
                s.answer(data.get('answers'), data.get('language', 'en'), data.get('reviewer'))
            elif path == '/api/approve-batch':
                s.approve_batch(data.get('rule'), data.get('language', 'en'), data.get('reviewer'))
            elif path == '/api/reject':
                s.reject(data.get('id'), data.get('reviewer'))
            elif path == '/api/reset':
                s.reset()
            elif path == '/api/ai-review':
                return self._json({**s.ai(data.get('consent') is True), 'state': s.state()})
            else:
                raise ApiError('Not found.', 404)
            return self._json(s.state())
        except Exception as error:  # noqa: BLE001
            self._fail(error)


def make_server(port: int = 8765, root: Path = ROOT) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    actual = server.server_address[1]
    server.allowed_hosts = {f'127.0.0.1:{actual}', f'localhost:{actual}'}  # type: ignore[attr-defined]
    server.session = Session(root)  # type: ignore[attr-defined]
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='AccessLoop local web interface')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    server = None
    for port in ([args.port] if args.port == 0 else range(args.port, args.port + 10)):
        try:
            server = make_server(port)
            break
        except OSError:
            continue
    if server is None:
        print(f'Could not bind a port starting at {args.port}.')
        return 1
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print(f'AccessLoop is running at {url}  (local only; press Ctrl+C to stop)')
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        server.server_close()
    return 0
