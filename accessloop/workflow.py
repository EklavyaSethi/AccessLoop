"""Explicit state machine with hash checks, reviewer approval and atomic rollback."""
from __future__ import annotations
import json
import os
import re
import inspect
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from bs4 import BeautifulSoup
from . import __version__
from .models import ScanResult, Proposal, Outcome
from .fixers import FixInputError
from .planner import materialize, plan, sha256
from .htmlsource import Edit, apply_edits
from .scanner import scan_html
from .ledger import Ledger, verify as verify_ledger
from .verification import announcement, uid_map, verify, verify_nodes
from .htmlsource import Doc

MAX_BYTES = 2 * 1024 * 1024


class WorkflowError(RuntimeError):
    pass


URL_ATTRS = {'src', 'href', 'data', 'action', 'formaction', 'poster', 'background', 'xlink:href', 'cite', 'longdesc',
             'codebase', 'manifest', 'ping', 'srcset', 'icon', 'dynsrc', 'lowsrc'}
ACTIVE_SCHEMES = ('javascript:', 'vbscript:', 'data:text/html', 'data:application', 'data:image/svg')


SAFE_SCHEMES = {'http', 'https', 'mailto', 'tel'}
SAFE_DATA_IMAGE = re.compile(r'^data:image/(png|jpe?g|gif|webp|avif|bmp|x-icon);', re.I)


def _normalise_url(value: str) -> str:
    v = ''.join(ch for ch in value if ch > ' ')            # browsers ignore embedded whitespace/control characters
    return v.replace('&#58;', ':').replace('&colon;', ':').replace('&#x3a;', ':').replace('&#X3A;', ':')


def _url_allowed(value: str, image_attr: bool) -> bool:
    """Allow-list: relative URLs, #fragments, http(s), mailto and tel; data: only for raster images in image
    attributes. Everything else (javascript:, vbscript:, file:, other data: types, unknown schemes) is refused."""
    for part in [value]:
        v = _normalise_url(part)
        m = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*):', v)
        if not m:
            continue                                         # relative URL or fragment
        scheme = m.group(1).lower()
        if scheme in SAFE_SCHEMES or (scheme == 'data' and image_attr and SAFE_DATA_IMAGE.match(v)):
            continue
        return False
    return True


def _active_url(value: str) -> bool:
    v = _normalise_url(value).lower()
    return any(v.startswith(s) or (',' + s) in v for s in ACTIVE_SCHEMES)


def validate_source(source: str, allow_scripts: bool = False) -> None:
    """Strict mode (default) refuses anything that could run code. Frames and objects are allowed: every network
    request is blocked during the scan, so they load nothing, but inline frame documents (srcdoc) and active URLs are
    refused. With allow_scripts=True a page with scripts is accepted for scanning and fixing; its scripts are removed
    from the browser's copy and blocked by a Content-Security-Policy, so they never run (scanner.scan_copy)."""
    if not source.strip() or len(source.encode('utf-8')) > MAX_BYTES:
        raise WorkflowError('Provide a nonempty HTML file under 2 MB.')
    soup = BeautifulSoup(source, 'html.parser')
    if soup.html is None:
        raise WorkflowError('The input must contain an <html> element.')
    if allow_scripts:
        return
    for tag in soup.find_all(True):
        name = (tag.name or '').lower().split(':')[-1]
        if name in {'script', 'base', 'applet', 'portal', 'frameset', 'frame'}:
            raise WorkflowError(f'Only static HTML is supported: <{name}> elements are not allowed.')
        for attr, val in tag.attrs.items():
            attr_l = attr.lower()
            text = ' '.join(val) if isinstance(val, list) else str(val or '')
            if attr_l.startswith('on'):
                raise WorkflowError('Inline event handlers (onclick and similar) are not supported.')
            if attr_l == 'srcdoc':
                raise WorkflowError('Inline frame documents (srcdoc) are not supported.')
            if attr_l in URL_ATTRS or attr_l.endswith(':href'):
                image_attr = attr_l in {'src', 'srcset', 'poster', 'lowsrc', 'dynsrc', 'icon'} and name != 'iframe'
                srcset = attr_l == 'srcset'
                values = [x.strip().split(' ')[0] for x in text.split(',')] if srcset else [text]
                if not all(_url_allowed(v, image_attr) for v in values if v):
                    raise WorkflowError('Only relative, #fragment, http(s), mailto and tel links (and data: images) are '
                                        'supported; javascript:, vbscript:, file: and other active URLs are refused.')
            if name == 'meta' and attr_l == 'content' and 'url' in text.lower() and _active_url(text.split('=', 1)[-1]):
                raise WorkflowError('A meta refresh to an active URL is not supported.')


def read_source(path: Path) -> str:
    # Keep CRLF intact when hashing and restoring the working copy.
    with path.open('r', encoding='utf-8', newline='') as handle:
        return handle.read()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.accessloop_', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class Workflow:
    def __init__(self, workspace: Path, scanner: Callable[[str], ScanResult] = scan_html):
        self.workspace = Path(workspace)
        self.scanner = scanner
        self.before: ScanResult | None = None
        self.current_scan: ScanResult | None = None
        self.proposals: tuple[Proposal, ...] = ()
        self._last_engine: dict = {}
        self.signer = None          # accounts.Identity of the signed-in reviewer; every event they cause is signed
        self.ledger: Ledger | None = None                # append-only, hash-chained audit log (audit.jsonl)
        self.loaded = False
        self.last_candidate: Proposal | None = None   # the exact proposal (with reviewer text) that was last applied
        self.best_practice = False                     # also run axe best-practice rules (set per scan)
        self.allow_scripts = False                     # accept pages with scripts (they are never run)
        self.extended = False                          # AccessLoop's own checks: reflow, text spacing, focus, open states
        self.assets_dir: Path | None = None            # folder the page's own CSS/images/fonts are loaded from

    def _scan(self, html: str, announce: tuple[int, ...] = ()) -> ScanResult:
        options = {}
        if announce and 'announce_uids' in _params(self.scanner):
            options['announce_uids'] = tuple(announce)
        if self.best_practice:
            options['best_practice'] = True
        if self.assets_dir is not None:
            options['assets_dir'] = self.assets_dir
        if self.extended and 'extended' in _params(self.scanner):
            options['extended'] = True
        return self.scanner(html, **options)

    @property
    def current_html(self) -> str:
        if not self.loaded:
            raise WorkflowError('Load an HTML file first.')
        return read_source(self.workspace / 'working.html')

    def load(self, source: str, allow_scripts: bool = False, assets_dir: Path | None = None) -> None:
        validate_source(source, allow_scripts=allow_scripts)
        self.allow_scripts = bool(allow_scripts)
        self.assets_dir = Path(assets_dir) if assets_dir else None
        self.workspace.mkdir(parents=True, exist_ok=True)
        atomic_write(self.workspace / 'original.html', source)
        atomic_write(self.workspace / 'working.html', source)
        atomic_write(self.workspace / 'changes.json', '[]')
        if self.ledger is None:
            self.ledger = Ledger(self.workspace / 'audit.jsonl')
        self.before = None
        self.current_scan = None
        self.proposals = ()
        self.loaded = True
        self._event('loaded', 'Original saved as a separate copy; it is never modified.', original_sha256=sha256(source),
                    scripts_present=bool(re.search(r'<script\b|\son[a-z]+\s*=', source, re.I)) or None,
                    allow_scripts=self.allow_scripts or None)

    @property
    def events(self) -> list[dict]:
        """Every audit entry ever written for this workspace (never cleared)."""
        return list(self.ledger.records) if self.ledger else []

    @property
    def run_events(self) -> list[dict]:
        """Entries since the latest load or reset: the decisions that shaped the current working copy."""
        events = self.events
        start = max((i for i, e in enumerate(events) if e['event'] in ('loaded', 'reset')), default=0)
        return events[start:]

    def scan(self, language: str = 'en', best_practice: bool | None = None, extended: bool | None = None) -> ScanResult:
        if best_practice is not None and bool(best_practice) != self.best_practice:
            self.best_practice = bool(best_practice)
            self.before = None   # a different rule set needs its own baseline
        if extended is not None and bool(extended) != self.extended:
            self.extended = bool(extended)
            self.before = None
        current = self.current_html
        t0 = time.perf_counter()
        scan_result = self._scan(current)  # failures propagate; no misleading blank report
        t1 = time.perf_counter()
        self.current_scan = scan_result
        if self.before is None:
            self.before = scan_result
        self.proposals = plan(current, scan_result.items, language=language)
        t2 = time.perf_counter()
        self._event('scanned', f'{len(scan_result.findings)} violation nodes, {len(scan_result.reviews)} needs-review nodes; '
                    f'{len(self.proposals)} fix proposals.', best_practice=self.best_practice,
                    counts=dict(scan_result.counts()), review_counts=dict(scan_result.review_counts()) or None,
                    proposals=len(self.proposals), input_proposals=sum(p.needs_input for p in self.proposals),
                    scan_ms=round((t1 - t0) * 1000), plan_ms=round((t2 - t1) * 1000))
        return scan_result

    def reject(self, proposal_id: str, reviewer: str | None = None) -> Outcome:
        p = self._lookup(proposal_id)
        self._event('rejected', f'{proposal_id}: no file modified.', proposal_id=proposal_id, rule=p.rule_id,
                    selector=p.selector, reviewer=reviewer)
        n = len(self.current_scan.findings) if self.current_scan else -1
        return Outcome('rejected', 'No file modified; rejection recorded.', n, n)

    def apply(self, proposal_id: str, approved: bool = False, language: str = 'en', values: dict | None = None,
              reviewer: str | None = None) -> Outcome:
        proposal = self._lookup(proposal_id)
        if not approved:
            return self.reject(proposal_id, reviewer)
        try:
            return self._apply(proposal, language, values, reviewer)
        except WorkflowError as error:
            # Every guardrail refusal is part of the record: stale diff, failed re-validation, missing or unsafe text.
            self._event('blocked', f'{proposal_id}: {error}', proposal_id=proposal_id, rule=proposal.rule_id,
                        reviewer=reviewer, guardrail=_guardrail(str(error)))
            raise

    def _apply(self, proposal: Proposal, language: str, values: dict | None, reviewer: str | None) -> Outcome:
        proposal_id = proposal.proposal_id
        current = self.current_html
        if sha256(current) != proposal.base_sha256:
            raise WorkflowError('Stale proposal blocked: working file changed after this diff was created.')
        if self.current_scan is None:
            raise WorkflowError('Scan before applying a proposal.')
        # Rebuild the patch from the original finding, server-side. Nothing supplied by a client or a model is trusted as HTML.
        if not 0 <= proposal.finding_index < len(self.current_scan.items):
            raise WorkflowError('Proposal failed restricted-patch validation.')
        finding = self.current_scan.items[proposal.finding_index]
        if proposal.needs_input and not values:
            raise WorkflowError('This fix needs the text only you can provide. Fill in the field before approving.')
        try:
            candidate = materialize(current, finding, proposal.finding_index, language, values if proposal.needs_input else None)
        except FixInputError as error:
            raise WorkflowError(str(error)) from error
        if candidate is None or candidate.proposal_id != proposal.proposal_id or candidate.needs_input or not candidate.new_html:
            raise WorkflowError('Proposal failed restricted-patch validation.')
        if not proposal.needs_input and candidate.new_html != proposal.new_html:
            raise WorkflowError('Proposal failed restricted-patch validation.')
        if not candidate.edits or apply_edits(current, list(candidate.edits)) != candidate.new_html:
            # the new file must differ from the current one by exactly the template's edits, nothing else
            raise WorkflowError('Proposal failed restricted-patch validation.')
        self.last_candidate = candidate
        previous_scan = self.current_scan
        backup_file = self.workspace / 'backups' / f'{len(self.events):04d}_{sha256(current)[:12]}.html'
        atomic_write(backup_file, current)
        atomic_write(self.workspace / 'working.html', candidate.new_html)
        t_write = time.perf_counter()
        targets = [(finding.rule_id, finding.uid)] if finding.uid is not None else []
        ann: dict = {}
        try:
            after, ok, detail, ann = self._judge(current, candidate.new_html, list(candidate.edits), previous_scan,
                                                 targets, candidate.rule_id)
            if not ok:
                raise WorkflowError(detail)
        except Exception as error:
            atomic_write(self.workspace / 'working.html', current)
            self._event('rolled_back', f'{proposal_id}: {error}', proposal_id=proposal_id, rule=candidate.rule_id,
                        announce_before=ann.get('before') or None, announce_after=ann.get('after') or None,
                        verify_ms=round((time.perf_counter() - t_write) * 1000), guardrail='verification gate',
                        selector=candidate.selector, reviewer=reviewer, before=candidate.before, after=candidate.after,
                        reviewer_text=_typed(values) if proposal.needs_input else None)
            return Outcome('rolled_back', str(error), len(previous_scan.findings), len(previous_scan.findings),
                           ann.get('before', ''), ann.get('after', ''))
        self.current_scan = after
        self.proposals = plan(self.current_html, after.items, language=language)
        self._record_op(list(candidate.edits), current, candidate.rule_id, proposal_id, candidate.selector)
        self._event('verified', f'{proposal_id}: {detail}', proposal_id=proposal_id, rule=candidate.rule_id,
                    announce_before=ann.get('before') or None, announce_after=ann.get('after') or None,
                    verify_ms=round((time.perf_counter() - t_write) * 1000), mode=proposal.mode,
                    selector=candidate.selector, reviewer=reviewer, before=candidate.before, after=candidate.after,
                    reviewer_text=_typed(values) if proposal.needs_input else None, backup=backup_file.name)
        return Outcome('verified', detail, len(previous_scan.findings), len(after.findings), ann.get('before', ''),
                       ann.get('after', ''))

    def _judge(self, current: str, new_html: str, edits: list, previous: ScanResult, targets: list[tuple[str, int]],
               rule: str) -> tuple[ScanResult, bool, str, dict]:
        """Scan the changed page and decide: rule counts must improve, AND at element level every targeted element
        must be fixed and no element may gain a new problem. Also returns what a screen reader announced for the
        (first) targeted element before and after."""
        mapping = uid_map(Doc(current), Doc(new_html), edits)
        new_targets = [mapping[u] for _, u in targets if u in mapping]
        after = self._scan(new_html, announce=tuple(new_targets[:5]))
        ok, detail = verify(previous, after, rule)
        if ok and targets:
            tolerate = rule != 'region' and after.counts()['landmark-one-main'] > 0 and previous.counts()['landmark-one-main'] > 0
            ok2, d2 = verify_nodes(previous, after, mapping, targets, tolerate)
            ok, detail = (ok, f'{detail} {d2}') if ok2 else (False, d2)
        first = next((f for f in previous.items if targets and f.uid == targets[0][1] and f.rule_id == targets[0][0]), None)
        ann = {'before': announcement(first.announce) if first else '',
               'after': announcement((after.announced or {}).get(new_targets[0])) if new_targets else ''}
        return after, ok, detail, ann

    def preview(self, proposal_id: str, language: str = 'en', values: dict | None = None) -> dict:
        """Dry run: build the fix and scan the changed page in memory, without writing anything. Shows what a screen
        reader will announce and whether the change would pass verification."""
        proposal = self._lookup(proposal_id)
        current = self.current_html
        if self.current_scan is None or sha256(current) != proposal.base_sha256:
            raise WorkflowError('Stale proposal blocked: working file changed after this diff was created.')
        finding = self.current_scan.items[proposal.finding_index]
        if proposal.needs_input and not values:
            raise WorkflowError('This fix needs the text only you can provide. Fill in the field before previewing.')
        try:
            cand = materialize(current, finding, proposal.finding_index, language, values if proposal.needs_input else None)
        except FixInputError as error:
            raise WorkflowError(str(error)) from error
        if cand is None or not cand.new_html:
            raise WorkflowError('Proposal failed restricted-patch validation.')
        targets = [(finding.rule_id, finding.uid)] if finding.uid is not None else []
        after, ok, detail, ann = self._judge(current, cand.new_html, list(cand.edits), self.current_scan, targets,
                                             cand.rule_id)
        return {'would_pass': ok, 'detail': detail, 'announce_before': ann['before'], 'announce_after': ann['after'],
                'violations_after': len(after.findings)}

    def apply_batch(self, proposal_ids: list[str], language: str = 'en', reviewer: str | None = None) -> Outcome:
        """Approve several automatic fixes for the same rule at once: one write, one re-scan, one verdict.

        Every patch is rebuilt server-side exactly as for a single approval. The batch is verified strictly: the rule
        must drop by at least one node per fix and no other rule may increase; otherwise the whole batch is rolled
        back and the fixes can still be approved one by one."""
        ids = list(dict.fromkeys(proposal_ids))
        if len(ids) < 2:
            raise WorkflowError('A batch needs at least two fixes.')
        proposals = [self._lookup(i) for i in ids]
        rules = {p.rule_id for p in proposals}
        if len(rules) != 1 or any(p.needs_input for p in proposals):
            raise WorkflowError('A batch may only contain automatic fixes for one rule.')
        rule = rules.pop()
        current = self.current_html
        if self.current_scan is None or any(p.base_sha256 != sha256(current) for p in proposals):
            self._event('blocked', 'Batch: stale proposals.', rule=rule, reviewer=reviewer, guardrail='stale-diff check')
            raise WorkflowError('Stale proposal blocked: working file changed after these diffs were created.')
        edits = []
        for p in proposals:
            if not 0 <= p.finding_index < len(self.current_scan.items):
                raise WorkflowError('Proposal failed restricted-patch validation.')
            cand = materialize(current, self.current_scan.items[p.finding_index], p.finding_index, language, None)
            if cand is None or cand.proposal_id != p.proposal_id or cand.new_html != p.new_html or not cand.edits:
                self._event('blocked', f'Batch: {p.proposal_id} failed re-validation.', rule=rule, reviewer=reviewer,
                            guardrail='patch re-validation')
                raise WorkflowError('Proposal failed restricted-patch validation.')
            edits += list(cand.edits)
        edits = list(dict.fromkeys(edits))     # several findings can share one page-level fix (e.g. one style rule)
        try:
            new_html = apply_edits(current, edits)
        except ValueError as error:
            self._event('blocked', 'Batch: fixes touch the same code.', rule=rule, reviewer=reviewer, guardrail='patch re-validation')
            raise WorkflowError('These fixes touch the same code; approve them one at a time.') from error
        previous = self.current_scan
        backup_file = self.workspace / 'backups' / f'{len(self.events):04d}_{sha256(current)[:12]}.html'
        atomic_write(backup_file, current)
        atomic_write(self.workspace / 'working.html', new_html)
        t_write = time.perf_counter()
        n = len(proposals)
        old_t = previous.counts()[rule] + previous.review_counts()[rule]
        targets = [(rule, self.current_scan.items[p.finding_index].uid) for p in proposals
                   if self.current_scan.items[p.finding_index].uid is not None]
        try:
            after, ok, detail, _ann = self._judge(current, new_html, edits, previous, targets, rule)
            new_t = after.counts()[rule] + after.review_counts()[rule]
            if ok and new_t > old_t - n:
                ok, detail = False, (f'Only {old_t - new_t} of {n} {rule} items were fixed ({old_t} → {new_t}); '
                                     'approve them one at a time to see which.')
            if not ok:
                raise WorkflowError(detail)
        except Exception as error:
            atomic_write(self.workspace / 'working.html', current)
            self._event('rolled_back', f'Batch of {n} {rule} fixes: {error}', rule=rule, batch=ids, reviewer=reviewer,
                        verify_ms=round((time.perf_counter() - t_write) * 1000), guardrail='verification gate')
            return Outcome('rolled_back', str(error), len(previous.findings), len(previous.findings))
        self.current_scan = after
        self.proposals = plan(self.current_html, after.items, language=language)
        self._record_op(edits, current, rule, f'batch of {n}', f'{n} elements')
        self._event('verified', f'Batch of {n} {rule} fixes: {detail}', rule=rule, batch=ids, reviewer=reviewer,
                    verify_ms=round((time.perf_counter() - t_write) * 1000), backup=backup_file.name, mode='batch')
        return Outcome('verified', f'{n} fixes applied together. {detail}', len(previous.findings), len(after.findings))

    # ---- undo one earlier fix -------------------------------------------------------------------------------
    def _ops_path(self) -> Path:
        return self.workspace / 'changes.json'

    def changes(self) -> list[dict]:
        """Every write since the last load/reset, oldest first: verified fixes and reverts, with their edits."""
        try:
            return json.loads(self._ops_path().read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return []

    def _record_op(self, edits: list, before_html: str, rule: str, label: str, selector: str, kind: str = 'fix',
                   reverts: int | None = None) -> None:
        ops = self.changes()
        ops.append({'n': len(ops), 'kind': kind, 'rule': rule, 'label': label, 'selector': selector, 'reverts': reverts,
                    'status': 'active', 'edits': [[e.start, e.end, e.text, before_html[e.start:e.end]]
                                                   for e in sorted(edits, key=lambda x: (x.start, x.end))]})
        atomic_write(self._ops_path(), json.dumps(ops, ensure_ascii=False))

    def revert(self, n: int, language: str = 'en', reviewer: str | None = None) -> Outcome:
        """Undo one earlier verified fix while keeping every later one. Refused if a later change touched the same
        code. The page is re-scanned: only the undone fix's own rule may come back; anything else getting worse
        means the undo is not written."""
        if self.current_scan is None:
            raise WorkflowError('Scan before undoing a fix.')
        ops = self.changes()
        if not 0 <= n < len(ops) or ops[n]['kind'] != 'fix' or ops[n]['status'] != 'active':
            raise WorkflowError('That fix cannot be undone (unknown, already undone, or not a fix).')
        target = ops[n]
        # where each of the fix's edits sits now: first inside the fix itself, then through every later write
        spans, delta = [], 0
        for start, end, text, old in target['edits']:
            spans.append([start + delta, start + delta + len(text), text, old])
            delta += len(text) - (end - start)
        for later in ops[n + 1:]:
            for ls, le, lt, _old in later['edits']:
                for sp in spans:
                    if le <= sp[0]:
                        sp[0] += len(lt) - (le - ls)
                        sp[1] += len(lt) - (le - ls)
                    elif ls >= sp[1]:
                        continue
                    else:
                        raise WorkflowError(f'A later change ({later["rule"]}) touched the same code. Undo that one first.')
        current = self.current_html
        for s, t, text, _old in spans:
            if current[s:t] != text:
                raise WorkflowError('The file no longer matches this fix; it cannot be undone safely.')
        inverse = [Edit(s, t, old) for s, t, _text, old in spans]
        new_html = apply_edits(current, inverse)
        previous = self.current_scan
        after = self._scan(new_html)
        old_c, new_c = previous.counts(), after.counts()
        worse = [r for r in set(old_c) | set(new_c) if r != target['rule'] and new_c[r] > old_c[r]]
        if worse:
            self._event('blocked', f'Undo of {target["label"]} refused: {", ".join(sorted(worse))} would get worse.',
                        rule=target['rule'], reviewer=reviewer, guardrail='verification gate')
            return Outcome('rolled_back', f'Undo refused: {", ".join(sorted(worse))} would get worse.', len(previous.findings),
                           len(previous.findings))
        backup_file = self.workspace / 'backups' / f'{len(self.events):04d}_{sha256(current)[:12]}.html'
        atomic_write(backup_file, current)
        atomic_write(self.workspace / 'working.html', new_html)
        ops[n]['status'] = 'reverted'
        atomic_write(self._ops_path(), json.dumps(ops, ensure_ascii=False))
        self._record_op(inverse, current, target['rule'], f'undo of {target["label"]}', target['selector'], kind='revert',
                        reverts=n)
        self.current_scan = after
        self.proposals = plan(new_html, after.items, language=language)
        self._event('reverted', f'Undid {target["label"]} ({target["rule"]}); later fixes kept.', rule=target['rule'],
                    reviewer=reviewer, backup=backup_file.name, reverted_change=n)
        return Outcome('verified', f'Undid the {target["rule"]} fix; every later fix is kept. {target["rule"]}: '
                                   f'{old_c[target["rule"]]} → {new_c[target["rule"]]}.', len(previous.findings), len(after.findings))

    def changed_elements(self) -> list[int]:
        """uids (in the current working copy) of elements touched by the fixes that are still in place."""
        ops = self.changes()
        spans = []
        for i, op in enumerate(ops):
            if op['kind'] != 'fix' or op['status'] != 'active':
                continue
            delta, mine = 0, []
            for start, end, text, _old in op['edits']:
                mine.append([start + delta, start + delta + len(text)])
                delta += len(text) - (end - start)
            ok = True
            for later in ops[i + 1:]:
                for ls, le, lt, _o in later['edits']:
                    for sp in mine:
                        if le <= sp[0]:
                            sp[0] += len(lt) - (le - ls)
                            sp[1] += len(lt) - (le - ls)
                        elif ls < sp[1]:
                            ok = False
            if ok:
                spans += mine
        doc = Doc(self.current_html)
        hit = []
        for s, t in spans:
            inside = [e for e in doc.elements if e.start <= s < (e.end_end or e.start_end) and e.tag not in ('html', 'body', 'head')]
            if inside:
                hit.append(max(inside, key=lambda e: e.start).uid)
        return sorted(set(hit))

    def screenshots(self) -> tuple[bytes, bytes]:
        """Original and repaired page as rendered in the sandbox; the repaired one has changed elements outlined."""
        from .scanner import screenshot
        original = read_source(self.workspace / 'original.html')
        return (screenshot(original, self.assets_dir),
                screenshot(self.current_html, self.assets_dir, tuple(self.changed_elements())))

    def reset(self) -> None:
        """Put the original back as the working copy. The audit log keeps everything and records the reset."""
        if not self.loaded:
            raise WorkflowError('Load a file first.')
        original = read_source(self.workspace / 'original.html')
        atomic_write(self.workspace / 'working.html', original)
        atomic_write(self._ops_path(), '[]')
        self.before = None
        self.current_scan = None
        self.proposals = ()
        self._event('reset', 'Working copy restored from the original. Earlier entries are kept.')

    def report_json(self) -> str:
        if not self.loaded:
            raise WorkflowError('Load a file first.')
        report = {
            'product': 'AccessLoop',
            'scope': 'Static HTML; automated WCAG rule checks; not a conformance certificate',
            'original_sha256': sha256(read_source(self.workspace / 'original.html')),
            'current_sha256': sha256(self.current_html),
            'baseline_counts': dict(self.before.counts()) if self.before else None,
            'current_counts': dict(self.current_scan.counts()) if self.current_scan else None,
            'unresolved': [asdict(f) for f in self.current_scan.findings] if self.current_scan else [],
            'audit_events': self.events,
            'audit_log': self.audit_status(),
        }
        return json.dumps(report, indent=2, ensure_ascii=False)

    def _lookup(self, proposal_id: str) -> Proposal:
        match = next((p for p in self.proposals if p.proposal_id == proposal_id), None)
        if match is None:
            raise WorkflowError('Unknown or expired proposal ID.')
        return match

    def audit_status(self) -> dict:
        ok, message, records = verify_ledger(self.workspace / 'audit.jsonl')
        return {'file': 'audit.jsonl', 'entries': len(records), 'verified': ok, 'message': message,
                'head_sha256': records[-1]['hash'] if ok and records else None}

    def _event(self, status: str, detail: str, signer=None, **fields) -> None:
        if self.ledger is None:
            return
        engine = (self.current_scan.engine if self.current_scan is not None else None) or self._last_engine or {}
        if self.current_scan is not None and self.current_scan.engine:
            self._last_engine = self.current_scan.engine
        versions = {'accessloop': __version__, **{k: str(v) for k, v in engine.items()}}
        self.ledger.append(status, detail, signer=signer or self.signer,
                           working_sha256=sha256(self.current_html) if self.loaded else None, versions=versions, **fields)


def _params(fn) -> set[str]:
    try:
        return set(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        return set()


def _guardrail(message: str) -> str:
    m = message.lower()
    if 'stale' in m:
        return 'stale-diff check'
    if 'validation' in m:
        return 'patch re-validation'
    if 'needs the text' in m or 'required' in m or 'choose' in m or 'cannot contain' in m or 'must be' in m:
        return 'reviewer-text validation'
    return 'other'


def _typed(values: dict | None) -> dict | None:
    """What the reviewer typed, as recorded in the audit log (short strings only)."""
    if not values:
        return None
    return {str(k)[:40]: (v if isinstance(v, bool) else str(v)[:200]) for k, v in values.items()}


def approve_all(engine: Workflow, values_for, reviewer: str | None = None, language: str = 'en', limit: int = 400) -> list[dict]:
    """Unattended approval loop used by the CLI (--approve-auto) and the validation runner.

    Automatic fixes for the same rule go in one batch first; if a batch is rolled back, that rule's fixes are tried one
    at a time. `values_for(proposal)` returns the reviewer's typed values, or None to skip a fix that needs text."""
    results: list[dict] = []
    tried: set = set()
    single: set = set()
    for _ in range(limit):
        todo = [p for p in engine.proposals if (p.rule_id, p.selector, p.before, p.line) not in tried]
        if not todo:
            break
        groups: dict[str, list] = {}
        for p in todo:
            if not p.needs_input and p.rule_id not in single:
                groups.setdefault(p.rule_id, []).append(p)
        batch = next((g for g in groups.values() if len(g) >= 2), None)
        t0 = time.perf_counter()
        if batch is not None:
            try:
                out = engine.apply_batch([p.proposal_id for p in batch], language=language, reviewer=reviewer)
                status, detail = out.status, out.detail
            except WorkflowError as error:
                status, detail = 'refused', str(error)
            results.append({'rule': batch[0].rule_id, 'mode': 'batch', 'size': len(batch), 'status': status,
                            'detail': detail[:200], 'seconds': round(time.perf_counter() - t0, 2)})
            if status != 'verified':
                single.add(batch[0].rule_id)
            continue
        p = todo[0]
        key = (p.rule_id, p.selector, p.before, p.line)
        values = values_for(p) if p.needs_input else None
        if p.needs_input and values is None:
            tried.add(key)
            results.append({'rule': p.rule_id, 'mode': 'input', 'size': 1, 'status': 'skipped', 'detail': 'needs reviewer text',
                            'seconds': 0})
            continue
        try:
            out = engine.apply(p.proposal_id, approved=True, language=language, values=values, reviewer=reviewer)
            status, detail = out.status, out.detail
        except WorkflowError as error:
            status, detail = 'refused', str(error)
        results.append({'rule': p.rule_id, 'mode': 'input' if p.needs_input else 'auto', 'size': 1, 'status': status,
                        'detail': detail[:200], 'seconds': round(time.perf_counter() - t0, 2)})
        if status != 'verified':
            tried.add(key)        # a verified fix disappears from the list by itself; only failures are remembered
    return results
