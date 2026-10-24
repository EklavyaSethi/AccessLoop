from __future__ import annotations
import re
from dataclasses import dataclass, asdict, field
from collections import Counter
from typing import Any


@dataclass(frozen=True)
class Finding:
    rule_id: str
    selector: str
    impact: str
    help: str
    description: str
    uid: int | None = None            # exact source element (data-al-uid) when the scan was instrumented
    html: str = ''
    data: Any = field(default=None, compare=False, hash=False)   # axe check data, e.g. colours for contrast
    kind: str = 'violation'           # 'violation' (axe failed it) or 'review' (axe could not decide: needs a human)
    announce: Any = field(default=None, compare=False, hash=False)   # what a screen reader announces for the element


@dataclass(frozen=True)
class ScanResult:
    findings: tuple[Finding, ...]
    incomplete: int = 0
    passed_rules: int = 0
    reviews: tuple[Finding, ...] = ()     # axe "needs review" nodes, kept separate from violations
    engine: Any = field(default=None, compare=False, hash=False)     # {'axe': version, 'browser': version}
    blocked: tuple = ()                   # requests the sandbox refused (resources that did not load)
    announced: Any = field(default=None, compare=False, hash=False)  # uid -> announcement, for requested elements

    @property
    def items(self) -> tuple[Finding, ...]:
        """Violations then needs-review nodes; proposal finding_index points into this tuple."""
        return self.findings + self.reviews

    def review_counts(self) -> Counter[str]:
        return Counter(f.rule_id for f in self.reviews)

    @classmethod
    def from_axe(cls, data: dict[str, Any]) -> 'ScanResult':
        findings = cls._nodes(data.get('violations', []), 'violation')
        reviews = cls._nodes(data.get('incomplete', []), 'review')
        return cls(tuple(findings), len(data.get('incomplete', [])), len(data.get('passes', [])), tuple(reviews),
                   engine=data.get('engine'), blocked=tuple(data.get('blocked') or ()),
                   announced={int(k): v for k, v in (data.get('announced') or {}).items() if str(k).isdigit()})

    @staticmethod
    def _nodes(results: list, kind: str) -> list[Finding]:
        findings = []
        for violation in results:
            for node in violation.get('nodes', []):
                targets = node.get('target') or ['(unknown element)']
                checks: dict[str, Any] = {}
                for group in ('any', 'all', 'none'):
                    for check in node.get(group) or []:
                        if check.get('data') is not None:
                            checks[str(check.get('id'))] = check['data']
                raw_uid = node.get('uid')
                findings.append(Finding(
                    rule_id=str(violation['id']),
                    selector=re.sub(r'\[data-al-uid="\d+"\]', '', str(targets[0])),
                    impact=str(violation.get('impact') or 'unknown'),
                    help=str(violation.get('help') or violation['id']),
                    description=str(node.get('failureSummary') or ''),
                    uid=int(raw_uid) if str(raw_uid).isdigit() else None,
                    html=re.sub(r' data-al-uid="\d+"', '', str(node.get('html') or ''))[:400],
                    data=checks or None,
                    kind=kind,
                    announce=node.get('announce'),
                ))
        return findings

    def counts(self) -> Counter[str]:
        return Counter(f.rule_id for f in self.findings)


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    rule_id: str
    selector: str
    explanation: str
    evidence: str
    before: str
    after: str
    base_sha256: str
    new_html: str
    finding_index: int = -1
    uid: int | None = None
    mode: str = 'auto'                # 'auto' or 'input'
    risk: str = 'low'
    fields: tuple = ()                # input mode: what the reviewer must type
    needs_input: bool = False
    line: int | None = None           # 1-based source line of the element
    edits: tuple = field(default=(), compare=False, repr=False)   # the offset edits behind new_html (for batch apply)
    files: tuple = field(default=(), compare=False, repr=False)   # ((relative path, text), ...) new files the fix creates


@dataclass(frozen=True)
class Outcome:
    status: str
    detail: str
    before_count: int
    after_count: int
    announce_before: str = ''        # what a screen reader announced for the element before the change
    announce_after: str = ''         # ... and after it (empty when unknown)

    def to_dict(self) -> dict:
        return asdict(self)
