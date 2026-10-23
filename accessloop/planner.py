"""Plans fixes. Parses the source once, maps each finding to an exact element, and asks the fixer for offset edits.

`plan()` keeps the original signature (source, findings, language) so existing callers and tests keep working.
"""
from __future__ import annotations
import hashlib

from .fixers import FIXERS, MODES, Draft, FixInputError  # noqa: F401 - re-exported
from .htmlsource import Doc, Element, apply_edits, shifted_span
from .models import Finding, Proposal


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def resolve(doc: Doc, finding: Finding) -> Element | None:
    if finding.uid is not None:
        return doc.by_uid.get(finding.uid)
    return doc.resolve_selector_id(finding.selector)


def _snippet(source: str, new_source: str, draft: Draft) -> tuple[str, str]:
    start, end = draft.focus
    n_start, n_end = shifted_span(draft.focus, draft.edits)
    before, after = source[start:end], new_source[n_start:n_end]
    return before.strip()[:600], after.strip()[:600]


def propose_one(doc: Doc, digest: str, index: int, finding: Finding, language: str = 'en',
                values: dict | None = None) -> Proposal | None:
    fixer = FIXERS.get(finding.rule_id)
    el = resolve(doc, finding)
    if fixer is None or el is None:
        return None
    draft = fixer(doc, el, finding, language, values)
    if draft is None:
        return None
    pid = f'{digest[:10]}-{index}-{finding.rule_id}'
    common = dict(proposal_id=pid, rule_id=finding.rule_id, selector=finding.selector, explanation=draft.explanation,
                  evidence=draft.evidence, base_sha256=digest, finding_index=index, uid=el.uid, mode=draft.mode,
                  risk=draft.risk, line=doc.source.count('\n', 0, el.start) + 1)
    if draft.mode == 'input' and values is None:
        before = doc.source[draft.focus[0]:draft.focus[1]].strip()[:600]
        return Proposal(**common, before=before, after=draft.preview or '…', new_html='', fields=tuple(draft.fields), needs_input=True)
    if not draft.edits:
        return None
    new_source = apply_edits(doc.source, draft.edits)
    if new_source == doc.source:
        return None
    before, after = _snippet(doc.source, new_source, draft)
    return Proposal(**common, before=before, after=after, new_html=new_source, fields=tuple(draft.fields),
                    edits=tuple(draft.edits))


def plan(source: str, findings: tuple[Finding, ...], language: str = 'en') -> tuple[Proposal, ...]:
    doc, digest = Doc(source), sha256(source)
    out = []
    for index, finding in enumerate(findings):
        proposal = propose_one(doc, digest, index, finding, language)
        if proposal is not None:
            out.append(proposal)
    return tuple(out)


def materialize(source: str, finding: Finding, index: int, language: str, values: dict | None) -> Proposal | None:
    """Rebuild one proposal from scratch (optionally with reviewer-typed values); used to re-validate before writing."""
    return propose_one(Doc(source), sha256(source), index, finding, language, values)
