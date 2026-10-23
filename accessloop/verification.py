"""Treat improvements as local evidence, never as a full WCAG compliance claim."""
from .models import ScanResult


def verify(before: ScanResult, after: ScanResult, target_rule: str) -> tuple[bool, str]:
    """A fix passes only if its rule improves (violations plus needs-review nodes) and no rule's violations increase."""
    old, new = before.counts(), after.counts()
    old_t = old[target_rule] + before.review_counts()[target_rule]
    new_t = new[target_rule] + after.review_counts()[target_rule]
    if new_t >= old_t:
        return False, f'Target rule {target_rule} did not improve ({old_t} → {new_t}).'
    notes = []
    for rule in sorted(set(old) | set(new)):
        if new[rule] > old[rule]:
            if rule == 'region' and target_rule != 'region' and new['landmark-one-main'] > 0 and old['landmark-one-main'] > 0:
                # The page has no main landmark, so every piece of content is "outside a region". New visible text
                # (a heading, a label) adds a node to that page-level finding without creating a new kind of problem.
                notes.append(f'region {old[rule]} → {new[rule]} (page has no main landmark yet; fix that to clear all region items)')
                continue
            return False, f'Automated regression: {rule} increased ({old[rule]} → {new[rule]}).'
    extra = ' Note: ' + '; '.join(notes) + '.' if notes else ''
    return True, f'Target rule improved ({old_t} → {new_t}); no increase in detected rule counts.{extra}'


# ---- per-element verification -------------------------------------------------------------------------------
def map_position(pos: int, edits) -> int | None:
    """Where an offset of the old source sits after `edits`; None when an edit replaced the text at that offset."""
    delta = 0
    for e in sorted(edits, key=lambda x: (x.start, x.end)):
        if e.end <= pos:
            delta += len(e.text) - (e.end - e.start)
        elif e.start < pos < e.end or (e.start == pos and e.end > pos):
            return None
    return pos + delta


def uid_map(old_doc, new_doc, edits) -> dict[int, int]:
    """Old element uid -> new element uid, following each element's start tag through the edits."""
    new_by_start = {e.start: e.uid for e in new_doc.elements}
    out: dict[int, int] = {}
    for e in old_doc.elements:
        pos = map_position(e.start, edits)
        if pos is not None and pos in new_by_start:
            out[e.uid] = new_by_start[pos]
    return out


def verify_nodes(before: ScanResult, after: ScanResult, mapping: dict[int, int], targets: list[tuple[str, int]],
                 tolerate_region: bool) -> tuple[bool, str]:
    """Element-level check, on top of the rule counts: each targeted (rule, element) must be gone, and no element
    may gain a problem it did not have before (including elements the fix inserted)."""
    had = {(f.rule_id, mapping.get(f.uid)) for f in before.items if f.uid is not None and f.uid in mapping}
    now = {(f.rule_id, f.uid) for f in after.items if f.uid is not None}
    for rule, old_uid in targets:
        new_uid = mapping.get(old_uid)
        if new_uid is not None and (rule, new_uid) in now:
            return False, f'The targeted element still has the {rule} problem.'
    fresh = sorted(p for p in now - had if not (tolerate_region and p[0] == 'region'))
    if fresh:
        rule, uid = fresh[0]
        more = f' (and {len(fresh) - 1} more)' if len(fresh) > 1 else ''
        return False, f'Automated regression: a new {rule} problem appeared on an element{more}.'
    return True, 'Every targeted element was fixed and no element gained a new problem.'


def announcement(info) -> str:
    """'Full name, edit text, required' style text from the scanner's announcement data."""
    if not info:
        return ''
    role = {'textbox': 'edit text', 'img': 'image', 'combobox': 'combo box', 'listbox': 'list box', 'spinbutton': 'spin button', 'searchbox': 'search box'}.get(info.get('role'),
                                                                                                     info.get('role') or '')
    parts = [f'“{info.get("name")}”' if info.get('name') else '(no name)', role] + list(info.get('states') or [])
    return ', '.join(p for p in parts if p)
