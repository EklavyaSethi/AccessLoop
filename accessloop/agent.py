"""Agent mode: AccessLoop repairs a page on its own, inside a policy a person sets, and stops for what only a person knows.

    perceive (scan) -> plan (fix proposals) -> policy gate -> act (write) -> verify (independent re-scan)
        -> commit, or roll back -> re-plan on the new page -> ... -> hand over (summary + questions for the person)

The policy is the human approval given in advance: which risk levels the agent may apply on its own, which rules are off
limits, how many changes it may make, and when it must stop (circuit breaker). Anything that needs words only a person
knows (alt text, names, titles) is never guessed: it is handed back as a question. Every step is in the audit log, and
the run itself is recorded with its policy, so a reviewer can see what the agent was allowed to do and what it did.
"""
from __future__ import annotations
import hashlib
import time
from collections import Counter
from dataclasses import dataclass, field, asdict

from .workflow import Workflow, WorkflowError


@dataclass
class Policy:
    risks: tuple = ('low',)                 # risk levels the agent may apply without asking ('low', 'medium')
    deny_rules: tuple = ()                  # rules the agent must never touch
    max_changes: int = 200                  # most writes in one run
    stop_after_rollbacks: int = 6           # circuit breaker: stop after this many rollbacks in a row
    batch: bool = True                      # apply identical fixes together (one write, one re-scan)

    def allows(self, p) -> tuple[bool, str]:
        if p.needs_input:
            return False, 'needs words only a person knows'
        if p.rule_id in self.deny_rules:
            return False, 'rule is off limits in this policy'
        if p.risk not in self.risks:
            return False, f'{p.risk}-risk fixes need a person in this policy'
        return True, ''

    def describe(self) -> str:
        parts = [f'applies {" and ".join(self.risks)}-risk automatic fixes', f'at most {self.max_changes} changes',
                 f'stops after {self.stop_after_rollbacks} rollbacks in a row']
        if self.deny_rules:
            parts.append('never touches ' + ', '.join(self.deny_rules))
        return '; '.join(parts) + '; never types text for you.'


@dataclass
class Step:
    n: int
    phase: str                  # perceive | plan | gate | act | verify | commit | rollback | escalate | stop
    title: str
    detail: str = ''
    rule: str = ''
    size: int = 0
    violations: int | None = None
    seconds: float = 0.0
    changes: list = field(default_factory=list)   # [{'line', 'selector', 'before', 'after'}] for writes


@dataclass
class Run:
    policy: Policy
    steps: list = field(default_factory=list)
    before: int = 0
    after: int = 0
    reviews_before: int = 0
    reviews_after: int = 0
    applied: int = 0            # individual fixes kept
    decisions: int = 0          # writes (a batch counts once)
    rolled_back: int = 0
    held: list = field(default_factory=list)        # proposals the policy kept for a person
    questions: list = field(default_factory=list)   # fixes that need typed text
    stopped: str = ''
    seconds: float = 0.0
    console: list = field(default_factory=list)     # (elapsed seconds, phase, text): what the agent did, line by line

    def to_dict(self) -> dict:
        d = asdict(self)
        d['policy_text'] = self.policy.describe()
        return d


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:10]


def _top(counts: dict, n: int = 4) -> str:
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    out = ', '.join(f'{k}×{v}' for k, v in items[:n])
    return out + (f', +{len(items) - n} more rules' if len(items) > n else '')


def run(engine: Workflow, policy: Policy | None = None, reviewer: str = 'AccessLoop agent', language: str = 'en',
        on_step=None, on_log=None, pace: float = 0.0) -> Run:
    """Repair the loaded page within `policy`.

    `on_step(step, run)` is called after every step and `on_log(line, run)` after every console line (live display).
    `pace` adds a pause after each step so people can follow it on screen; it never changes what the agent does, and the
    timings in the console are the real ones."""
    policy = policy or Policy()
    if not engine.loaded:
        raise WorkflowError('Load a page first.')
    r = Run(policy=policy)
    t_start = time.perf_counter()
    paused = [0.0]          # display pauses, left out of every reported time

    def say(phase, text):
        line = (round(time.perf_counter() - t_start - paused[0], 3), phase, text)
        r.console.append(line)
        if on_log:
            on_log(line, r)

    def step(phase, title, detail='', rule='', size=0, seconds=0.0, changes=None):
        s = Step(len(r.steps) + 1, phase, title, detail, rule, size,
                 len(engine.current_scan.findings) if engine.current_scan else None, round(seconds, 2), list(changes or []))
        r.steps.append(s)
        if on_step:
            on_step(s, r)
        if pace and phase not in ('act',):
            time.sleep(pace)
            paused[0] += pace
        return s

    engine._event('agent_started', 'Agent run started. Policy: ' + policy.describe(), reviewer=reviewer,
                  policy=asdict(policy))
    say('policy', policy.describe())
    say('perceive', f'working copy sha256 {_sha(engine.current_html)}… ({len(engine.current_html):,} bytes); original kept read-only')
    t = time.perf_counter()
    fresh = engine.current_scan is None
    if fresh:
        say('perceive', 'launching sandboxed Chromium: scripts off, network blocked; injecting axe-core')
    scan = engine.current_scan or engine.scan(language=language)
    eng = scan.engine or {}
    if eng:
        say('perceive', 'engine ' + ', '.join(f'{k} {v}' for k, v in list(eng.items())[:3]))
    r.before, r.reviews_before = len(scan.findings), len(scan.reviews)
    say('perceive', f'scan: {r.before} violation nodes [{_top(dict(scan.counts()))}]; {r.reviews_before} need review'
        + (f'; {len(scan.blocked)} network requests blocked' if scan.blocked else '')
        + (f' ({time.perf_counter() - t:.2f}s)' if fresh else ' (latest scan of this exact file, reused)'))
    step('perceive', f'Scanned the page: {r.before} violations, {r.reviews_before} items that need checking',
         seconds=time.perf_counter() - t)
    _allowed = sum(policy.allows(p)[0] for p in engine.proposals)
    _text = sum(p.needs_input for p in engine.proposals)
    say('plan', f'{len(engine.proposals)} fix proposals from {len({p.rule_id for p in engine.proposals})} templates → '
        f'{_allowed} allowed by policy, {_text} need a person\'s words, {len(engine.proposals) - _allowed - _text} held')
    step('plan', f'Planned {len(engine.proposals)} fixes', f'{sum(p.needs_input for p in engine.proposals)} need words '
         'from a person')

    failed: set = set()          # (rule, selector, before, line) that did not verify
    single: set = set()          # rules whose batch was rolled back: try one by one
    streak = 0
    while True:
        if r.decisions >= policy.max_changes:
            r.stopped = f'Reached the limit of {policy.max_changes} changes.'
            break
        if streak >= policy.stop_after_rollbacks:
            r.stopped = f'Circuit breaker: {streak} rollbacks in a row.'
            break
        allowed, held = [], {}
        for p in engine.proposals:
            if (p.rule_id, p.selector, p.before, p.line) in failed:
                continue
            ok, why = policy.allows(p)
            (allowed.append(p) if ok else held.setdefault(p.proposal_id, (p, why)))
        if not allowed:
            break
        groups: dict[str, list] = {}
        for p in allowed:
            groups.setdefault(p.rule_id, []).append(p)
        batch = None
        if policy.batch:
            batch = next((g for rule, g in groups.items() if len(g) >= 2 and rule not in single), None)
        todo = batch or [allowed[0]]
        rule, n = todo[0].rule_id, len(todo)
        where = ', '.join(f'line {p.line}' if p.line else p.selector for p in todo[:3]) + (' …' if n > 3 else '')
        say('gate', f'{rule} ×{n} · risk {todo[0].risk} · allowed ({where})')
        sha_before = _sha(engine.current_html)
        rule_counts_before = dict(engine.current_scan.counts()) if engine.current_scan else {}
        step('gate', f'Policy allows {n} “{rule}” fix{"es" if n > 1 else ""}', f'risk {todo[0].risk}; '
             + ('one write for all of them' if n > 1 else todo[0].selector), rule, n)
        t = time.perf_counter()
        try:
            if n > 1:
                out = engine.apply_batch([p.proposal_id for p in todo], language=language, reviewer=reviewer)
            else:
                out = engine.apply(todo[0].proposal_id, approved=True, language=language, reviewer=reviewer)
            status, detail = out.status, out.detail
        except WorkflowError as error:
            status, detail = 'refused', str(error)
        r.decisions += 1
        secs = time.perf_counter() - t
        written = todo
        if n == 1 and engine.last_candidate is not None and engine.last_candidate.proposal_id == todo[0].proposal_id:
            written = [engine.last_candidate]          # the exact text that was written
        changes = [{'line': p.line, 'selector': p.selector, 'before': p.before, 'after': p.after} for p in written]
        if status != 'refused':
            say('act', f'wrote {n} edit{"s" if n > 1 else ""} to working.html (sha {sha_before}… → '
                f'{_sha(engine.current_html) if status == "verified" else "restored " + sha_before}…)')
            after_counts = dict(engine.current_scan.counts()) if engine.current_scan else {}
            changed = {k for k in set(rule_counts_before) | set(after_counts) if rule_counts_before.get(k, 0) != after_counts.get(k, 0)}
            delta = ', '.join(f'{k} {rule_counts_before.get(k, 0)}→{after_counts.get(k, 0)}' for k in sorted(changed)[:4]) or 'no rule counts changed'
            say('verify', f're-scan: {delta}; {len(engine.current_scan.findings) if engine.current_scan else "?"} violations left ({secs:.2f}s)')
        step('act', f'Wrote the change to the working copy', detail='original file untouched', rule=rule, size=n)
        if status == 'verified':
            r.applied += n
            streak = 0
            last = engine.events[-1] if engine.events else {}
            say('commit', f'kept · audit entry #{len(engine.events)} hash {str(last.get("hash", ""))[:12]}…'
                + (' · signed' if last.get('sig') else ''))
            step('commit', f'Verified and kept: {n} fix{"es" if n > 1 else ""}', detail, rule, n, secs, changes)
        else:
            r.rolled_back += 1
            streak += 1
            if n > 1:
                single.add(rule)
            else:
                p = todo[0]
                failed.add((p.rule_id, p.selector, p.before, p.line))
            say('rollback', ('undone, file restored byte for byte: ' if status == 'rolled_back' else 'refused before writing: ')
                + detail[:140] + (f' · circuit breaker {streak}/{policy.stop_after_rollbacks}' if streak else ''))
            step('rollback', 'Did not verify, so it was undone' if status == 'rolled_back' else 'Refused before writing',
                 detail, rule, n, secs, changes)
    # hand over to the person
    for p in engine.proposals:
        ok, why = policy.allows(p)
        if p.needs_input:
            r.questions.append({'id': p.proposal_id, 'rule': p.rule_id, 'selector': p.selector, 'line': p.line,
                                'question': p.explanation, 'fields': [dict(f) for f in p.fields]})
        elif not ok:
            r.held.append({'id': p.proposal_id, 'rule': p.rule_id, 'selector': p.selector, 'line': p.line, 'why': why})
    cur = engine.current_scan
    r.after, r.reviews_after = len(cur.findings), len(cur.reviews)
    r.seconds = round(time.perf_counter() - t_start - paused[0], 2)
    if r.questions or r.held:
        say('escalate', f'{len(r.questions)} fixes need words only a person knows; {len(r.held)} are outside the policy → '
            'handed to the reviewer')
        step('escalate', f'Handed {len(r.questions) + len(r.held)} fixes to you',
             f'{len(r.questions)} need your words, {len(r.held)} need your approval')
    say('stop', (r.stopped + ' ' if r.stopped else '') + f'{r.before} → {r.after} violations · {r.applied} fixes kept in '
        f'{r.decisions} writes · {r.rolled_back} rolled back · {r.seconds}s of agent work')
    step('stop', r.stopped or 'Nothing more the agent may do on its own',
         f'{r.before} → {r.after} violations, {r.applied} fixes kept, {r.rolled_back} rolled back, {r.seconds} s')
    engine._event('agent_finished', f'Agent run finished: {r.before} → {r.after} violations; {r.applied} fixes kept in '
                  f'{r.decisions} writes; {r.rolled_back} rolled back; {len(r.questions)} questions and {len(r.held)} '
                  f'held fixes handed to a person.' + (f' {r.stopped}' if r.stopped else ''), reviewer=reviewer,
                  violations_before=r.before, violations_after=r.after, applied=r.applied, rolled_back=r.rolled_back,
                  questions=len(r.questions), held=len(r.held), seconds=r.seconds)
    return r
