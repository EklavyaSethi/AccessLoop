"""More fix templates: ARIA hygiene, structure (lists, tables, landmarks, headings), media, and spacing.

Same contract as fixers.py: each fixer returns a Draft of offset edits (or asks the reviewer for input), and every
applied change is re-verified by a fresh browser scan and rolled back if anything gets worse.
"""
from __future__ import annotations
import html as html_std
import re

from .fixers import (Draft, FixInputError, _aria_label, _bad_tokens, _tag_focus, _text_field, clean_text, fixer)
from .htmlsource import VOID, Doc, Edit, Element, descendants, extent_end, has_real_end_tag, rename_tag, wrap

REMOVE = '__remove__'


# ---- small helpers -----------------------------------------------------------------------------------------
def _style_set(doc: Doc, el: Element, decls: dict[str, str]) -> list[Edit]:
    """Set (or replace) CSS declarations in the element's inline style, keeping everything else."""
    current = el.value('style') or ''
    parts = [p.strip() for p in current.split(';') if p.strip()]
    keep = [p for p in parts if p.split(':', 1)[0].strip().lower() not in decls]
    keep += [f'{k}: {v}' for k, v in decls.items()]
    return doc.set_attr(el, 'style', '; '.join(keep))


def _focusable(e: Element) -> bool:
    if e.get('disabled') is not None:
        return False
    tab = (e.value('tabindex') or '').strip()
    if tab.lstrip('-').isdigit():
        return int(tab) >= 0
    if e.tag == 'a':
        return e.get('href') is not None
    if e.tag == 'input':
        return (e.value('type') or '').lower() != 'hidden'
    return e.tag in {'button', 'select', 'textarea', 'iframe', 'summary', 'embed', 'object', 'audio', 'video'} or \
        e.get('contenteditable') is not None


def _describe(doc: Doc, e: Element) -> str:
    bits = [e.tag]
    if e.value('id'):
        bits.append(f'#{e.value("id")}')
    if e.value('class'):
        bits.append('.' + '.'.join((e.value('class') or '').split()[:2]))
    text = doc.text_of(e)[:50]
    return f'<{"".join(bits)}> “{text}”' if text else f'<{"".join(bits)}>'


def _line(doc: Doc, e: Element) -> int:
    return doc.source.count('\n', 0, e.start) + 1


def _role_tokens(el: Element) -> list[str]:
    return (el.value('role') or '').lower().split()


def _check(f, key: str) -> dict:
    data = (f.data or {}).get(key)
    return data if isinstance(data, dict) else {}


def _select(name: str, label: str, options: list[tuple[str, str]], help: str = '') -> dict:
    return {'name': name, 'label': label, 'kind': 'select', 'required': True, 'options': options, 'help': help}


def _choose(values: dict, name: str, options: list[tuple[str, str]]) -> str:
    choice = str(values.get(name, ''))
    if choice not in {v for v, _ in options}:
        raise FixInputError('Choose an option from the list.')
    return choice


def _consecutive_run(doc: Doc, el: Element, tags: set[str]) -> tuple[Element, Element]:
    """The run of adjacent sibling elements around `el` whose tags are in `tags` (only whitespace between them)."""
    siblings = el.parent.children if el.parent else doc.root_children
    i = siblings.index(el)
    lo = hi = i
    while lo > 0 and siblings[lo - 1].tag in tags and not doc.source[extent_end(siblings[lo - 1]):siblings[lo].start].strip():
        lo -= 1
    while hi + 1 < len(siblings) and siblings[hi + 1].tag in tags and \
            not doc.source[extent_end(siblings[hi]):siblings[hi + 1].start].strip():
        hi += 1
    return siblings[lo], siblings[hi]


# ---- names and labels --------------------------------------------------------------------------------------
@fixer('label-content-name-mismatch', mode='auto')
def name_mismatch(doc, el, f, language, values):
    visible = doc.text_of(el)
    if el.get('aria-label') is None or not 1 <= len(visible) <= 80:
        return None
    return Draft(doc.remove_attr(el, 'aria-label'), _tag_focus(el),
                 'Let the visible text be the accessible name, so speech-input users can say what they see.',
                 f'Visible text "{visible}" but aria-label "{el.value("aria-label")}". Removing aria-label makes the name '
                 f'"{visible}". If the extra words matter, add them to the visible text instead.', risk='medium')


@fixer('label-title-only', mode='auto')
def title_only(doc, el, f, language, values):
    title = re.sub(r'\s+', ' ', el.value('title') or '').strip()
    if not 1 <= len(title) <= 120 or el.get('aria-label') is not None:
        return None
    return Draft(doc.set_attr(el, 'aria-label', title), _tag_focus(el),
                 'A tooltip (title) is not a reliable label. Give the field a real accessible name from the same words.',
                 f'Only label is title="{title}". A visible <label> is still better; this is the minimal safe fix.')


@fixer('object-alt', 'frame-title-unique', mode='input')
def typed_name(doc, el, f, language, values):
    if f.rule_id == 'frame-title-unique':
        return _aria_label(doc, el, values, 'Several frames share this title. Type a title that says what this one contains.',
                           'Frame title', attr='title')
    return _aria_label(doc, el, values, 'Embedded objects need a text alternative. Type what it shows.', 'Alternative text')


# ---- ARIA hygiene -----------------------------------------------------------------------------------------
DEPRECATED_ROLES = {'directory': 'list', 'doc-biblioentry': 'listitem', 'doc-endnote': 'listitem'}


@fixer('aria-deprecated-role', mode='auto')
def deprecated_role(doc, el, f, language, values):
    tokens = _role_tokens(el)
    swap = [t for t in tokens if t in DEPRECATED_ROLES]
    if not swap:
        return None
    new = ' '.join(DEPRECATED_ROLES.get(t, t) for t in tokens)
    return Draft(doc.set_attr(el, 'role', new), _tag_focus(el), 'Replace the deprecated role with its current equivalent.',
                 f'role="{el.value("role")}" → role="{new}"')


@fixer('aria-braille-equivalent', mode='auto')
def braille(doc, el, f, language, values):
    edits = doc.remove_attr(el, 'aria-braillelabel') + doc.remove_attr(el, 'aria-brailleroledescription')
    if not edits:
        return None
    return Draft(edits, _tag_focus(el), 'Remove braille-only labels that have no matching spoken label.',
                 'aria-braillelabel / aria-brailleroledescription must not be used without a non-braille equivalent.')


@fixer('aria-conditional-attr', mode='auto')
def conditional_attr(doc, el, f, language, values):
    data = _check(f, 'aria-conditional-attr')
    names = ['aria-checked'] if data.get('messageKey') == 'checkbox' else \
        sorted({t.split('=')[0].strip().lower() for t in _bad_tokens(f) if t.startswith('aria-')})
    edits = [e for n in names for e in doc.remove_attr(el, n)]
    if not edits:
        return None
    return Draft(edits, _tag_focus(el), 'Remove ARIA state that contradicts the native element.',
                 f'Removed {", ".join(names)}: the browser already exposes this state for <{el.tag}>.', risk='medium')


@fixer('aria-prohibited-attr', mode='auto')
def prohibited_attr(doc, el, f, language, values):
    names = _check(f, 'aria-prohibited-attr').get('prohibited') or []
    names = [n for n in names if isinstance(n, str) and el.get(n) is not None]
    if not names:
        return None
    edits = [e for n in names for e in doc.remove_attr(el, n)]
    return Draft(edits, _tag_focus(el), 'Remove ARIA naming that is not allowed (and ignored) on this element.',
                 f'{", ".join(names)} is not supported on a <{el.tag}> without a role, so screen readers may not announce it. '
                 'If the words matter, show them as visible text.', risk='medium')


@fixer('aria-allowed-role', 'presentation-role-conflict', 'aria-text', mode='auto')
def drop_roles(doc, el, f, language, values):
    if f.rule_id == 'presentation-role-conflict':
        bad = {'none', 'presentation'}
    elif f.rule_id == 'aria-text':
        bad = {'text'}
    else:
        bad = {t.lower() for t in _bad_tokens(f)}
    if not bad & set(_role_tokens(el)):
        return None
    edits = doc.remove_attr_value_tokens(el, 'role', bad)
    native = el.tag in {'a', 'button', 'input', 'select', 'textarea', 'summary', 'iframe'}
    if f.rule_id == 'presentation-role-conflict' and el.get('tabindex') is not None and not native:
        edits += doc.remove_attr(el, 'tabindex')     # a decorative element should not take keyboard focus either
    return Draft(edits, _tag_focus(el),
                 'Remove a role that conflicts with what the element really is.',
                 f'role="{el.value("role")}" on <{el.tag}>: removed {", ".join(sorted(bad & set(_role_tokens(el))))}.',
                 risk='medium')


IMPLICIT_LANDMARK = {'nav': 'navigation', 'aside': 'complementary', 'main': 'main', 'header': 'banner',
                     'footer': 'contentinfo', 'search': 'search'}
LANDMARK_ROLES = {'navigation', 'complementary', 'main', 'banner', 'contentinfo', 'search', 'region', 'form'}


def _landmark_role(e: Element) -> str | None:
    explicit = [t for t in _role_tokens(e) if t in LANDMARK_ROLES]
    if explicit:
        return explicit[0]
    return IMPLICIT_LANDMARK.get(e.tag) if not _role_tokens(e) else None


def _named(e: Element) -> bool:
    return bool((e.value('aria-label') or '').strip() or (e.value('aria-labelledby') or '').strip())


@fixer('landmark-unique', mode='input')
def landmark_unique(doc, el, f, language, values):
    role = _check(f, 'landmark-is-unique').get('role') or _landmark_role(el)
    peers = [e for e in doc.elements if _landmark_role(e) == role and not _named(e)][:6]
    if not role or el not in peers:
        return None
    flds = tuple(_text_field(f'n{i}', f'Name for the {role} at line {_line(doc, p)} ({_describe(doc, p)[:50]})',
                             'For example "Main menu", "Footer links".') for i, p in enumerate(peers))
    if values is None:
        return Draft(focus=_tag_focus(el), explanation=f'There are several {role} regions with no names, so screen-reader '
                     'users cannot tell them apart. Type a short, different name for each.',
                     evidence=f'{len(peers)} unnamed {role} landmark(s).', mode='input', fields=flds, preview='aria-label="…"')
    names = [clean_text(values.get(f'n{i}'), 1, 60, 'Region name') for i in range(len(peers))]
    if len({n.lower() for n in names}) != len(names):
        raise FixInputError('Each region needs a different name.')
    edits = [e for p, n in zip(peers, names) for e in doc.set_attr(p, 'aria-label', n)]
    return Draft(edits, (peers[0].start, peers[-1].start_end), 'Give each region the name you typed.',
                 'Reviewer-provided names: ' + ', '.join(f'"{n}"' for n in names))


@fixer('landmark-no-duplicate-banner', 'landmark-no-duplicate-contentinfo', mode='input')
def duplicate_landmark(doc, el, f, language, values):
    role = 'banner' if f.rule_id.endswith('banner') else 'contentinfo'
    tag = 'header' if role == 'banner' else 'footer'
    peers = [e for e in doc.elements if _landmark_role(e) == role and (e.tag == tag or role in _role_tokens(e))
             and not any(a.tag in {'article', 'aside', 'main', 'nav', 'section'} for a in _ancestors(e))][:4]
    if len(peers) < 2:
        return None
    options = [(str(p.uid), f'{_describe(doc, p)} (line {_line(doc, p)})') for p in peers]
    word = 'header' if role == 'banner' else 'footer'
    flds = (_select('keep', f'There are {len(peers)} page {word}s. Which one is the real page {word}?', options),
            _text_field('name', f'Name for the other {word} area', 'For example "Market status". It becomes a named region.'))
    if values is None:
        return Draft(focus=_tag_focus(el), explanation=f'A page should have only one {word} landmark. Pick the real one; '
                     'the others become named regions, so nothing they contain is lost.',
                     evidence=f'{len(peers)} top-level <{tag}> / role="{role}" elements.', mode='input', fields=flds,
                     preview='<section aria-label="…">')
    keep = _choose(values, 'keep', options)
    name = clean_text(values.get('name'), 1, 60, 'Region name')
    others = [p for p in peers if str(p.uid) != keep]
    edits: list[Edit] = []
    for k, p in enumerate(others, start=1):
        label = name if len(others) == 1 else f'{name} {k}'
        if p.tag == tag and has_real_end_tag(doc, p) and p.get('role') is None:
            edits += rename_tag(doc, p, 'section')     # <header>/<footer> may not take role="region"; a named <section> is one
        elif p.tag != tag:
            edits += doc.set_attr(p, 'role', ' '.join(t if t != role else 'region' for t in _role_tokens(p)))
        else:
            return None                                # unusual markup: leave it to a person
        edits += doc.set_attr(p, 'aria-label', label)
    if not edits:
        return None
    return Draft(edits, (peers[0].start, peers[-1].start_end), f'Keep one page {word}; the others become named regions.',
                 f'Reviewer kept one {word}; the other area is now the region "{name}".', risk='medium')


@fixer('landmark-no-duplicate-main', mode='input')
def duplicate_main(doc, el, f, language, values):
    peers = [e for e in doc.elements if (e.tag == 'main' and e.get('role') is None) or 'main' in _role_tokens(e)]
    peers = [e for e in peers if e.get('hidden') is None][:4]
    if len(peers) < 2:
        return None
    options = [(str(p.uid), f'{_describe(doc, p)} (line {_line(doc, p)})') for p in peers]
    flds = (_select('keep', f'There are {len(peers)} main content areas. Which one is the real main content?', options),
            _text_field('name', 'Name for the other area', 'For example "Offers". It becomes a named region.'))
    if values is None:
        return Draft(focus=_tag_focus(el), explanation='A page should have one main landmark, so screen-reader users can jump '
                     'straight to the content. Pick the real one; the others become named regions, so nothing is lost.',
                     evidence=f'{len(peers)} <main> / role="main" elements.', mode='input', fields=flds,
                     preview='<section aria-label="…">', risk='medium')
    keep = _choose(values, 'keep', options)
    name = clean_text(values.get('name'), 1, 60, 'Region name')
    others = [p for p in peers if str(p.uid) != keep]
    edits: list[Edit] = []
    for k, p in enumerate(others, start=1):
        label = name if len(others) == 1 else f'{name} {k}'
        if p.tag == 'main' and has_real_end_tag(doc, p) and p.get('role') is None:
            edits += rename_tag(doc, p, 'section')
        elif p.tag != 'main':
            edits += doc.set_attr(p, 'role', ' '.join(t if t != 'main' else 'region' for t in _role_tokens(p)))
        else:
            return None
        edits += doc.set_attr(p, 'aria-label', label)
    return Draft(edits, (peers[0].start, peers[-1].start_end), 'Keep one main landmark; the others become named regions.',
                 f'Reviewer kept one main area; the other is now the region "{name}".', risk='medium')


def _orphan_headers(doc: Doc, table: Element) -> list[Element]:
    """<th> cells with no data cell in their row or column. None if the table is too complex to judge (spans, nesting)."""
    inner = descendants(doc, table)
    if any(e.tag == 'table' for e in inner) or any(e.get('colspan') or e.get('rowspan') for e in inner if e.tag in {'td', 'th'}):
        return []
    rows = [[c for c in r.children if c.tag in {'td', 'th'}] for r in inner if r.tag == 'tr']
    has_data_col: dict[int, bool] = {}
    for r in rows:
        for i, c in enumerate(r):
            if c.tag == 'td' and doc.text_of(c):
                has_data_col[i] = True
    out = []
    for r in rows:
        row_data = any(c.tag == 'td' and doc.text_of(c) for c in r)
        for i, c in enumerate(r):
            if c.tag == 'th' and not row_data and not has_data_col.get(i) and has_real_end_tag(doc, c):
                out.append(c)
    return out


@fixer('th-has-data-cells', mode='input')
def th_no_data(doc, el, f, language, values):
    table = el if el.tag == 'table' else next((a for a in _ancestors(el) if a.tag == 'table'), None)
    orphans = _orphan_headers(doc, table) if table is not None else []
    if not orphans:
        return None
    names = ', '.join(f'"{doc.text_of(c)[:30]}"' for c in orphans[:5])
    options = [('td', f'{"They are" if len(orphans) > 1 else "It is"} not a header: make {"them" if len(orphans) > 1 else "it"} normal cells')]
    flds = (_select('choice', f'These header cells label no data: {names}. What are they?', options,
                    'If the data is added later by a script, reject this fix instead.'),)
    if values is None:
        return Draft(focus=(orphans[0].start, extent_end(orphans[-1])), explanation='A header cell should label data cells. '
                     'If it does not, screen readers announce a header that leads nowhere. Only you know whether data is '
                     'added later.', evidence=f'Header cells with no data in their row or column: {names}.', mode='input',
                     fields=flds, preview='<td>…</td>', risk='medium')
    _choose(values, 'choice', options)
    edits: list[Edit] = []
    for c in orphans:
        edits += rename_tag(doc, c, 'td')
        if c.get('scope') is not None:
            edits += doc.remove_attr(c, 'scope')
    return Draft(edits, (orphans[0].start, extent_end(orphans[-1])), 'Turn header cells that label no data into normal cells.',
                 f'Reviewer confirmed {names} are not headers.', risk='medium')


def _ancestors(e: Element) -> list[Element]:
    out, p = [], e.parent
    while p is not None:
        out.append(p)
        p = p.parent
    return out


CHILD_ROLE = {'list': 'listitem', 'listbox': 'option', 'menu': 'menuitem', 'menubar': 'menuitem', 'tablist': 'tab',
              'tree': 'treeitem'}


@fixer('aria-required-children', mode='auto')
def required_children(doc, el, f, language, values):
    roles = [t for t in _role_tokens(el) if t in CHILD_ROLE]
    kids = [c for c in el.children if c.tag not in {'script', 'template'}]
    if not roles or not kids or any(c.get('role') is not None for c in kids):
        return None
    child_role = CHILD_ROLE[roles[0]]
    edits = [e for c in kids for e in doc.set_attr(c, 'role', child_role)]
    return Draft(edits, (el.start, extent_end(el)), f'Give each item inside role="{roles[0]}" the role "{child_role}".',
                 f'role="{roles[0]}" contains {len(kids)} element(s) with no item role.', risk='medium')


@fixer('aria-required-parent', mode='auto')
def required_parent(doc, el, f, language, values):
    role = next((t for t in _role_tokens(el) if t in set(CHILD_ROLE.values()) | {'row', 'cell', 'gridcell'}), None)
    if role is None:
        return None
    return Draft(doc.remove_attr_value_tokens(el, 'role', {role}), _tag_focus(el),
                 f'Remove role="{role}": it only means something inside its parent widget, and there is none here.',
                 f'role="{role}" outside any {", ".join((f.data or {}).get("aria-required-parent") or ["parent"])}.',
                 risk='medium')


@fixer('aria-hidden-focus', mode='input')
def hidden_focus(doc, el, f, language, values):
    inner = [e for e in descendants(doc, el) if _focusable(e)]
    if el.get('aria-hidden') is None:
        return None
    options = [('show', 'It should be visible to everyone: stop hiding it (remove aria-hidden)'),
               ('unfocus', f'It should stay hidden: take its {len(inner)} control(s) out of the tab order')]
    fld = _select('choice', 'This content is hidden from screen readers but can still be focused. Which is right?', options)
    if values is None:
        return Draft(focus=_tag_focus(el), explanation='Hidden content must not be reachable with the keyboard.',
                     evidence=f'{len(inner)} focusable element(s) inside aria-hidden content.', mode='input', fields=(fld,),
                     preview='aria-hidden … / tabindex="-1"')
    if _choose(values, 'choice', options) == 'show':
        return Draft(doc.remove_attr(el, 'aria-hidden'), _tag_focus(el), 'Stop hiding this content from assistive technology.',
                     'Reviewer chose: visible to everyone.')
    if not inner:
        return None
    edits = [e for x in inner for e in doc.set_attr(x, 'tabindex', '-1')]
    return Draft(edits, (el.start, extent_end(el)), 'Keep the content hidden and remove its controls from the tab order.',
                 f'Reviewer chose: stays hidden. tabindex="-1" added to {len(inner)} control(s).', risk='medium')


BOOL = ['true', 'false']
ENUM = {
    'aria-expanded': BOOL, 'aria-selected': BOOL, 'aria-hidden': BOOL, 'aria-atomic': BOOL, 'aria-busy': BOOL,
    'aria-disabled': BOOL, 'aria-modal': BOOL, 'aria-multiline': BOOL, 'aria-multiselectable': BOOL,
    'aria-readonly': BOOL, 'aria-required': BOOL, 'aria-checked': BOOL + ['mixed'], 'aria-pressed': BOOL + ['mixed'],
    'aria-current': ['page', 'step', 'location', 'date', 'time', 'true', 'false'],
    'aria-haspopup': ['false', 'true', 'menu', 'listbox', 'tree', 'grid', 'dialog'],
    'aria-invalid': ['false', 'true', 'grammar', 'spelling'], 'aria-live': ['off', 'polite', 'assertive'],
    'aria-orientation': ['horizontal', 'vertical'], 'aria-sort': ['ascending', 'descending', 'none', 'other'],
    'aria-autocomplete': ['none', 'inline', 'list', 'both'],
}
NUMERIC = {'aria-level', 'aria-posinset', 'aria-setsize', 'aria-valuenow', 'aria-valuemin', 'aria-valuemax',
           'aria-colcount', 'aria-colindex', 'aria-colspan', 'aria-rowcount', 'aria-rowindex', 'aria-rowspan'}
IDREFS = {'aria-labelledby', 'aria-describedby', 'aria-controls', 'aria-owns', 'aria-activedescendant',
          'aria-errormessage', 'aria-details', 'aria-flowto'}


def _value_field(name: str, required_attr: bool = False) -> dict:
    if name in ENUM:
        opts = [(v, v) for v in ENUM[name]] + ([] if required_attr else [(REMOVE, 'Remove this attribute')])
        return _select(name, f'Correct value for {name}', opts)
    if name == 'aria-level':
        return _select(name, 'Heading level', [(str(i), f'Level {i}') for i in range(1, 7)])
    return {'name': name, 'label': f'Value for {name}', 'kind': 'text', 'required': True, 'max': 40,
            'help': 'A number' if name in NUMERIC else ''}


def _validated(name: str, raw: object) -> str | None:
    if name in ENUM or name == 'aria-level':
        allowed = ENUM.get(name, [str(i) for i in range(1, 7)]) + [REMOVE]
        value = str(raw)
        if value not in allowed:
            raise FixInputError(f'Choose a value for {name} from the list.')
        return None if value == REMOVE else value
    value = clean_text(raw, 1, 40, f'Value for {name}')
    if name in NUMERIC and not re.fullmatch(r'-?\d+(\.\d+)?', value):
        raise FixInputError(f'{name} must be a number.')
    return value


@fixer('aria-required-attr', mode='input')
def required_attr(doc, el, f, language, values):
    names = [n for n in (f.data or {}).get('aria-required-attr') or [] if isinstance(n, str) and n.startswith('aria-')]
    if not names or len(names) > 4:
        return None
    flds = tuple(_value_field(n, required_attr=True) for n in names)
    if values is None:
        return Draft(focus=_tag_focus(el), explanation=f'role="{el.value("role")}" needs {", ".join(names)} to describe its state.',
                     evidence='The current state cannot be guessed from the page; choose it.', mode='input', fields=flds,
                     preview=' '.join(f'{n}="…"' for n in names))
    edits: list[Edit] = []
    chosen = []
    for n in names:
        v = _validated(n, values.get(n))
        if v is None:
            raise FixInputError(f'{n} is required for this role.')
        edits += doc.set_attr(el, n, v)
        chosen.append(f'{n}="{v}"')
    return Draft(edits, _tag_focus(el), 'Add the required ARIA state you chose.', 'Reviewer chose ' + ', '.join(chosen))


@fixer('aria-valid-attr-value', mode='mixed')
def attr_value(doc, el, f, language, values):
    names = sorted({t.split('=')[0].strip().lower() for t in _bad_tokens(f) if t.startswith('aria-')})
    names = [n for n in names if el.get(n) is not None]
    if not names:
        return None
    if all(n in IDREFS for n in names) and values is None:
        edits: list[Edit] = []
        notes = []
        for n in names:
            tokens = (el.value(n) or '').split()
            missing = {t for t in tokens if t not in doc.ids}
            if not missing:
                return None
            edits += doc.remove_attr_value_tokens(el, n, missing)
            notes.append(f'{n}: removed reference(s) to missing id {", ".join(sorted(missing))}')
        return Draft(edits, _tag_focus(el), 'Remove references to ids that do not exist on the page.', '; '.join(notes),
                     risk='medium')
    if any(n in IDREFS for n in names) or len(names) > 4:
        return None
    flds = tuple(_value_field(n) for n in names)
    if values is None:
        current = ', '.join(f'{n}="{el.value(n)}"' for n in names)
        return Draft(focus=_tag_focus(el), explanation='This ARIA attribute has a value browsers do not understand. Choose the right one.',
                     evidence=f'Current: {current}', mode='input', fields=flds, preview=' '.join(f'{n}="…"' for n in names))
    edits = []
    for n in names:
        v = _validated(n, values.get(n))
        edits += doc.remove_attr(el, n) if v is None else doc.set_attr(el, n, v)
    return Draft(edits, _tag_focus(el), 'Use a valid ARIA value.', 'Reviewer-chosen values applied.')


@fixer('duplicate-id-aria', mode='auto')
def duplicate_id(doc, el, f, language, values):
    value = el.value('id')
    same = doc.ids.get(value or '', [])
    if not value or len(same) < 2:
        return None
    edits: list[Edit] = []
    renamed = []
    for k, e in enumerate(same[1:], start=2):
        new = f'{value}-{k}'
        while new in doc.ids:
            new += '-x'
        edits += doc.set_attr(e, 'id', new)
        renamed.append(f'line {_line(doc, e)} → id="{new}"')
    return Draft(edits, (same[0].start, extent_end(same[-1])),
                 'Make the repeated id unique. References keep pointing at the first element, as browsers already do.',
                 f'id="{value}" appears {len(same)} times; ' + '; '.join(renamed), risk='medium')


@fixer('form-field-multiple-labels', mode='input')
def multiple_labels(doc, el, f, language, values):
    fid = el.value('id')
    labels = [e for e in doc.elements if e.tag == 'label' and fid and e.value('for') == fid]
    wrapped = el.parent is not None and any(a.tag == 'label' for a in [el.parent])
    if len(labels) < 2 or wrapped:
        return None
    options = [(str(lb.uid), f'Keep “{doc.text_of(lb)[:60]}” (line {_line(doc, lb)})') for lb in labels]
    fld = _select('keep', 'This field has several labels. Which one is its real label?', options)
    if values is None:
        return Draft(focus=_tag_focus(el), explanation='A field should have exactly one label.',
                     evidence=f'{len(labels)} <label for="{fid}"> elements.', mode='input', fields=(fld,),
                     preview='one <label for> kept')
    keep = _choose(values, 'keep', options)
    edits = [e for lb in labels if str(lb.uid) != keep for e in doc.remove_attr(lb, 'for')]
    return Draft(edits, (labels[0].start, el.start_end), 'Keep one label; the others stay as visible text only.',
                 'Reviewer chose the label to keep.')


# ---- spacing, size and links ---------------------------------------------------------------------------------
@fixer('avoid-inline-spacing', mode='auto')
def inline_spacing(doc, el, f, language, values):
    style = el.value('style') or ''
    new = re.sub(r'((?:letter|word)-spacing|line-height)(\s*:[^;!]*)!\s*important', r'\1\2', style, flags=re.I)
    new = re.sub(r'\s+;', ';', new).strip()
    if new == style.strip():
        return None
    return Draft(doc.set_attr(el, 'style', new), _tag_focus(el),
                 'Let readers override text spacing (remove !important from spacing styles).',
                 'Users who need wider letter, word or line spacing could not override these styles.')


@fixer('link-in-text-block', mode='auto')
def link_in_text(doc, el, f, language, values):
    if el.tag != 'a':
        return None
    return Draft(_style_set(doc, el, {'text-decoration': 'underline'}), _tag_focus(el),
                 'Underline the link so it is not distinguished by colour alone.',
                 'Link inside a paragraph looked like plain text except for its colour.')


@fixer('target-size', mode='auto')
def target_size(doc, el, f, language, values):
    if el.tag not in {'button', 'a', 'input', 'select', 'label', 'summary'} and 'button' not in _role_tokens(el):
        return None
    if any(a.tag in {'a', 'button'} for a in [el.parent] if a is not None) or \
            any(_focusable(d) for d in descendants(doc, el)):
        return None   # nested controls: a structure problem (nested-interactive), not a size problem
    decls = {'min-width': '24px', 'min-height': '24px'}
    if el.tag in {'a', 'label'}:
        decls['display'] = 'inline-block'
    size = _check(f, 'target-size')
    return Draft(_style_set(doc, el, decls), _tag_focus(el), 'Make the click/tap target at least 24 × 24 CSS pixels.',
                 f'Target is {size.get("width", "?")} × {size.get("height", "?")} px; the minimum is 24 × 24.', risk='medium')


@fixer('skip-link', mode='auto')
def skip_link(doc, el, f, language, values):
    href = (el.value('href') or '').strip()
    if el.tag != 'a' or not href.startswith('#'):
        return None
    main = next((e for e in doc.elements if e.tag == 'main' or 'main' in _role_tokens(e)), None)
    if main is None:
        return None
    edits: list[Edit] = []
    target = main.value('id')
    if not target or len(doc.ids.get(target, [])) != 1:
        target = 'main-content'
        while target in doc.ids:
            target += '-1'
        edits += doc.set_attr(main, 'id', target)
    edits += doc.set_attr(el, 'href', '#' + target)
    return Draft(edits, _tag_focus(el), 'Point the skip link at the main content.',
                 f'href="{href}" pointed at nothing; main content is <{main.tag}> on line {_line(doc, main)}.')


# ---- landmarks and headings -------------------------------------------------------------------------------
def _main_candidates(doc: Doc) -> list[Element]:
    body = doc.find_first('body')
    if body is None:
        return []
    ok_tags = {'div', 'section', 'article'}          # elements on which role="main" is allowed

    def fits(c: Element) -> bool:
        # Wrapping the page header/footer/menu inside "main" would nest landmarks: never offer that.
        return c.tag in ok_tags and not _role_tokens(c) and \
            not any(_landmark_role(d) for d in descendants(doc, c))
    level1 = list(body.children)
    level2 = [g for c in level1 if c.tag in ok_tags for g in c.children]
    return [c for c in level1 + level2 if fits(c)][:12]


@fixer('bypass', 'landmark-one-main', mode='input')
def add_main(doc, el, f, language, values):
    if any(e.tag == 'main' or 'main' in _role_tokens(e) for e in doc.elements):
        return None
    cands = _main_candidates(doc)
    span = _wrap_range(doc)
    options = [(str(c.uid), f'{_describe(doc, c)} (line {_line(doc, c)})') for c in cands]
    if span is not None:
        first, last = span
        options.append(('wrap', f'Everything from line {_line(doc, first)} to line {_line(doc, last)} '
                                f'(between the page header/menu and footer): wrap it in <main>'))
    if not options:
        return None
    fld = _select('main', 'Which part of the page is the main content?', options,
                  'Screen-reader and keyboard users can jump straight to it.')
    anchor = cands[0] if cands else span[0]
    if values is None:
        return Draft(focus=_tag_focus(anchor), explanation='The page has no main landmark, so keyboard and screen-reader '
                     'users cannot skip past repeated content.', evidence='No <main> or role="main" on the page.',
                     mode='input', fields=(fld,), preview='role="main" / <main>')
    choice = _choose(values, 'main', options)
    if choice == 'wrap':
        first, last = span
        return Draft(wrap(first, last, '<main>', '</main>'), (first.start, extent_end(last)),
                     'Wrap the page content in a <main> element.',
                     f'Reviewer chose lines {_line(doc, first)}–{_line(doc, last)} as the main content. <main> displays '
                     'like a <div>; check any CSS that targets direct children of <body>.', risk='medium')
    chosen = doc.by_uid[int(choice)]
    return Draft(doc.set_attr(chosen, 'role', 'main'), _tag_focus(chosen), 'Mark the part you chose as the main content.',
                 f'Reviewer chose {_describe(doc, chosen)} as the main content.')


def _wrap_range(doc: Doc) -> tuple[Element, Element] | None:
    """The run of <body> children between the page header/menu (and skip links) and the footer, if it is clean."""
    body = doc.find_first('body')
    if body is None:
        return None
    kids = [c for c in body.children]
    lead = {'header', 'nav', 'script', 'style', 'noscript', 'template', 'link', 'meta'}
    trail = {'footer', 'script', 'style', 'noscript', 'template', 'link'}
    i, j = 0, len(kids) - 1
    while i <= j and (kids[i].tag in lead or (kids[i].tag == 'a' and (kids[i].value('href') or '').startswith('#'))):
        i += 1
    while j >= i and kids[j].tag in trail:
        j -= 1
    run = kids[i:j + 1]
    if not run or any(_landmark_role(e) in {'banner', 'contentinfo', 'main'} for e in run) or \
            any(e.tag not in VOID and not e.self_closed and e.end_end is None for e in run):
        return None
    return run[0], run[-1]


@fixer('landmark-banner-is-top-level', 'landmark-contentinfo-is-top-level', mode='auto')
def landmark_top(doc, el, f, language, values):
    # (landmark-main-is-top-level is not here: removing a nested main role leaves the page with no main at all,
    # which the re-scan rightly reports. Moving the main content out of its container is a structural edit.)
    role = {'landmark-banner-is-top-level': 'banner', 'landmark-contentinfo-is-top-level': 'contentinfo'}[f.rule_id]
    if role not in _role_tokens(el):
        return None
    return Draft(doc.remove_attr_value_tokens(el, 'role', {role}), _tag_focus(el),
                 f'Remove the explicit {role} role from an element nested inside another landmark.',
                 f'role="{role}" is only valid at the top level of the page.', risk='medium')


def _heading_level(e: Element) -> int | None:
    m = re.fullmatch(r'h([1-6])', e.tag)
    lvl = e.value('aria-level')
    if lvl and lvl.strip().isdigit() and (m or 'heading' in _role_tokens(e)):
        return int(lvl)
    return int(m.group(1)) if m else None


@fixer('heading-order', mode='auto')
def heading_order(doc, el, f, language, values):
    mine = _heading_level(el)
    prev = None
    for e in doc.elements:
        if e is el:
            break
        lvl = _heading_level(e)
        if lvl is not None:
            prev = lvl
    if mine is None or prev is None or mine <= prev + 1:
        return None
    # Renumber the outline once, in document order: no heading may be more than one level below the heading before
    # it. Only aria-level changes, so nothing looks different; every later skip is fixed by the same edit.
    edits: list[Edit] = []
    changed = []
    prev_new = None
    for e in doc.elements:
        lvl = _heading_level(e)
        if lvl is None:
            continue
        new = lvl if prev_new is None else min(lvl, prev_new + 1)
        if new != lvl:
            edits += doc.set_attr(e, 'aria-level', str(new))
            changed.append(e)
        prev_new = new
    if el not in changed:
        return None
    return Draft(edits, _tag_focus(el), 'Fix skipped heading levels for assistive technology without changing how they look.',
                 f'Heading level {mine} follows level {prev}. {len(changed)} heading(s) on the page are renumbered with '
                 'aria-level so no level is skipped. Consider changing the tags too.', risk='medium')


@fixer('page-has-heading-one', mode='input')
def heading_one(doc, el, f, language, values):
    container = next((e for e in doc.elements if e.tag == 'main' or 'main' in _role_tokens(e)), None) or doc.find_first('body')
    if container is None or container.content is None:
        return None
    fld = _text_field('text', 'Main heading for this page', 'For example "Open a savings account".')
    if values is None:
        return Draft(focus=_tag_focus(container), explanation='The page has no level-one heading. Type one; it is added at '
                     'the start of the main content.', evidence='No <h1> on the page.', mode='input', fields=(fld,),
                     preview='<h1>…</h1>')
    text = clean_text(values.get('text'), 2, 120, 'Heading')
    pos = container.start_end
    return Draft([Edit(pos, pos, f'<h1>{html_std.escape(text, quote=False)}</h1>')], (container.start, container.start_end),
                 'Add the main heading you typed.', f'Reviewer-provided heading: "{text}"')


@fixer('empty-heading', mode='input')
def empty_heading(doc, el, f, language, values):
    span = el.content
    if span is None or doc.text_of(el):
        return None
    fld = _text_field('text', 'Heading text', 'What is this section about?')
    if values is None:
        return Draft(focus=(el.start, extent_end(el)), explanation='Empty headings are announced as blank. Type the heading.',
                     evidence=f'<{el.tag}> has no text.', mode='input', fields=(fld,), preview=f'<{el.tag}>…</{el.tag}>')
    text = clean_text(values.get('text'), 1, 120, 'Heading text')
    return Draft([Edit(span[0], span[1], html_std.escape(text, quote=False))], (el.start, extent_end(el)),
                 'Add the heading text you typed.', f'Reviewer-provided heading: "{text}"')


# ---- images, media and frames --------------------------------------------------------------------------------
@fixer('image-redundant-alt', mode='auto')
def redundant_alt(doc, el, f, language, values):
    if el.tag != 'img' or not (el.value('alt') or '').strip():
        return None
    return Draft(doc.set_attr(el, 'alt', ''), _tag_focus(el), 'The same words are already next to the image; mark it decorative.',
                 f'alt="{el.value("alt")}" repeats the nearby text, so screen readers say it twice.', risk='medium')


@fixer('server-side-image-map', mode='auto')
def server_map(doc, el, f, language, values):
    if el.get('ismap') is None:
        return None
    return Draft(doc.remove_attr(el, 'ismap'), _tag_focus(el), 'Remove the server-side image map; the surrounding link still works.',
                 'ismap sends mouse coordinates, which keyboard users cannot produce.', risk='medium')



@fixer('video-caption', mode='input')
def video_caption(doc, el, f, language, values):
    if el.tag != 'video' or el.content is None:
        return None
    flds = (_text_field('src', 'Captions file (WebVTT) path', 'For example "media/intro.en.vtt". It must exist on your site.'),)
    if values is None:
        return Draft(focus=_tag_focus(el), explanation='Videos with speech need captions. Give the path of the captions file.',
                     evidence='<video> has no <track kind="captions">.', mode='input', fields=flds,
                     preview='<track kind="captions" src="…">')
    src = clean_text(values.get('src'), 3, 200, 'Captions file path')
    if re.match(r'(?i)\s*(javascript|data|vbscript):', src) or '"' in src or not re.search(r'\.vtt(\?.*)?$', src, re.I):
        raise FixInputError('Give the path of a .vtt captions file (http/https or a relative path).')
    code = language if re.fullmatch(r'[a-z]{2}(?:-[A-Z]{2})?', language or '') else 'en'
    tag = (f'<track kind="captions" src="{html_std.escape(src, quote=True)}" srclang="{code}" '
           f'label="Captions" default>')
    return Draft([Edit(el.start_end, el.start_end, tag)], (el.start, el.start_end),
                 'Attach the captions file you named.', f'Reviewer-provided captions file: {src}')



@fixer('meta-refresh', mode='input')
def meta_refresh(doc, el, f, language, values):
    if el.tag != 'meta':
        return None
    content = el.value('content') or ''
    m = re.match(r'\s*\d+(?:\.\d+)?\s*[;,]?\s*(?:url\s*=\s*)?(.*)$', content, re.I)
    url = (m.group(1).strip().strip('\'"') if m else '')
    options = ([('now', f'Redirect immediately to {url[:60]}')] if url else []) + [('remove', 'Remove the automatic refresh')]
    fld = _select('choice', 'The page refreshes or redirects by itself after a delay. What should happen?', options)
    if values is None:
        return Draft(focus=_tag_focus(el), explanation='Timed refreshes move people away before they finish reading.',
                     evidence=f'content="{content}"', mode='input', fields=(fld,), preview='meta refresh …')
    if _choose(values, 'choice', options) == 'now':
        return Draft(doc.set_attr(el, 'content', f'0; url={url}'), _tag_focus(el), 'Redirect at once instead of after a delay.',
                     'Reviewer chose an immediate redirect.')
    end = el.start_end
    return Draft([Edit(el.start, end, '')], (el.start, end), 'Remove the automatic refresh.', 'Reviewer chose to remove it.',
                 risk='medium')


# ---- lists and definition lists -----------------------------------------------------------------------------
@fixer('list', mode='auto')
def list_children(doc, el, f, language, values):
    if el.tag not in {'ul', 'ol'}:
        return None
    edits: list[Edit] = []
    notes = []
    for c in el.children:
        if c.tag in {'script', 'template'}:
            continue
        if c.tag == 'li':
            if c.get('role') is not None and 'listitem' not in _role_tokens(c):
                edits += doc.remove_attr(c, 'role')
                notes.append(f'removed role="{c.value("role")}" from <li> (line {_line(doc, c)})')
        elif c.tag in {'div', 'p', 'span'} and c.get('role') is None and has_real_end_tag(doc, c):
            edits += rename_tag(doc, c, 'li')
            notes.append(f'<{c.tag}> → <li> (line {_line(doc, c)})')
        else:
            edits += wrap(c, c, '<li>', '</li>')
            notes.append(f'wrapped <{c.tag}> in <li> (line {_line(doc, c)})')
    if not edits:
        return None
    return Draft(edits, (el.start, extent_end(el)), 'Lists may only contain list items. Make each child a list item.',
                 '; '.join(notes), risk='medium')


@fixer('listitem', 'dlitem', mode='auto')
def orphan_items(doc, el, f, language, values):
    parent = el.parent
    if f.rule_id == 'listitem':
        if el.tag != 'li':
            return None
        if parent is not None and parent.tag in {'ul', 'ol', 'menu'}:
            roles = _role_tokens(parent)
            if roles and 'list' not in roles:
                return Draft(doc.remove_attr(parent, 'role'), _tag_focus(parent), 'Restore the list’s native list role.',
                             f'role="{parent.value("role")}" on <{parent.tag}> hides that it is a list.', risk='medium')
            return None
        first, last = _consecutive_run(doc, el, {'li'})
        open_tag, close_tag, what = '<ul style="margin:0;padding:0">', '</ul>', 'list'
    else:
        if el.tag not in {'dt', 'dd'} or (parent is not None and parent.tag == 'dl'):
            return None
        first, last = _consecutive_run(doc, el, {'dt', 'dd'})
        siblings = el.parent.children if el.parent else doc.root_children
        run = siblings[siblings.index(first):siblings.index(last) + 1]
        if not ({'dt', 'dd'} <= {e.tag for e in run}):
            return None    # a term without a description (or the reverse) needs a content decision
        open_tag, close_tag, what = '<dl>', '</dl>', 'definition list'
    if any(e.end_end is None for e in (first, last)) or (first is not el and first.uid > el.uid):
        return None
    return Draft(wrap(first, last, open_tag, close_tag), (first.start, extent_end(last)),
                 f'Put these items inside a {what} so they are announced as one.',
                 f'<{el.tag}> on line {_line(doc, el)} is not inside a {what}.', risk='medium')


@fixer('definition-list', mode='input')
def definition_list(doc, el, f, language, values):
    bad = [c for c in el.children if c.tag not in {'dt', 'dd', 'div', 'script', 'template'} and has_real_end_tag(doc, c)][:6]
    if el.tag != 'dl' or not bad:
        return None
    options = [('dt', 'A term (dt)'), ('dd', 'A description (dd)')]
    flds = tuple(_select(f'c{i}', f'Line {_line(doc, c)}: {_describe(doc, c)} is…', options) for i, c in enumerate(bad))
    if values is None:
        return Draft(focus=(el.start, extent_end(el)), explanation='Definition lists may only contain terms and descriptions.',
                     evidence=f'{len(bad)} other element(s) inside <dl>.', mode='input', fields=flds, preview='<dt>/<dd>')
    edits = [e for i, c in enumerate(bad) for e in rename_tag(doc, c, _choose(values, f'c{i}', options))]
    return Draft(edits, (el.start, extent_end(el)), 'Turn each stray element into the term or description you chose.',
                 'Reviewer chose the role of each item.', risk='medium')


# ---- tables -------------------------------------------------------------------------------------------------
@fixer('scope-attr-valid', mode='auto')
def scope_valid(doc, el, f, language, values):
    if el.get('scope') is None:
        return None
    return Draft(doc.remove_attr(el, 'scope'), _tag_focus(el), 'Remove a scope attribute that is invalid here.',
                 f'scope="{el.value("scope")}" on <{el.tag}>.')


@fixer('table-duplicate-name', mode='auto')
def table_dup_name(doc, el, f, language, values):
    if el.get('summary') is None:
        return None
    return Draft(doc.remove_attr(el, 'summary'), _tag_focus(el), 'Remove the summary that repeats the caption.',
                 'Screen readers would read the same text twice.')


@fixer('td-headers-attr', mode='auto')
def td_headers(doc, el, f, language, values):
    cells = [e for e in descendants(doc, el) if e.tag in {'td', 'th'}]
    ids_here = {e.value('id') for e in cells if e.value('id')}
    edits: list[Edit] = []
    notes = []
    for c in cells:
        tokens = (c.value('headers') or '').split()
        bad = {t for t in tokens if t not in ids_here or t == c.value('id')}
        if c.get('headers') is not None and bad:
            edits += doc.remove_attr_value_tokens(c, 'headers', bad)
            notes.append(f'line {_line(doc, c)}: removed {", ".join(sorted(bad))}')
    if not edits:
        return None
    return Draft(edits, (el.start, el.start_end), 'Remove header references that point outside this table.',
                 '; '.join(notes), risk='medium')


@fixer('empty-table-header', mode='input')
def empty_th(doc, el, f, language, values):
    if el.tag != 'th' or el.content is None or doc.text_of(el):
        return None
    flds = (_text_field('text', 'Header text', 'What does this column or row contain?', required=False),
            {'name': 'not_header', 'label': 'This cell is not a header (turn it into a normal cell)', 'kind': 'checkbox',
             'required': False})
    if values is None:
        return Draft(focus=(el.start, extent_end(el)), explanation='Table headers need text, or should be normal cells.',
                     evidence='<th> is empty.', mode='input', fields=flds, preview='<th>…</th>')
    if values.get('not_header') in (True, 'true', 'on', '1', 1):
        return Draft(rename_tag(doc, el, 'td'), (el.start, extent_end(el)), 'Turn the empty header into a normal cell.',
                     'Reviewer said this is not a header.')
    text = clean_text(values.get('text'), 1, 80, 'Header text')
    span = el.content
    return Draft([Edit(span[0], span[1], html_std.escape(text, quote=False))], (el.start, extent_end(el)),
                 'Add the header text you typed.', f'Reviewer-provided header: "{text}"')


# ---- keyboard ----------------------------------------------------------------------------------------------
@fixer('accesskeys', mode='auto')
def accesskeys(doc, el, f, language, values):
    key = (el.value('accesskey') or '').strip().lower()
    if not key:
        return None
    same = [e for e in doc.elements if (e.value('accesskey') or '').strip().lower() == key]
    if len(same) < 2:
        return None
    edits = [x for e in same[1:] for x in doc.remove_attr(e, 'accesskey')]
    return Draft(edits, (same[0].start, extent_end(same[-1])), 'Keep the shortcut key on the first element only.',
                 f'accesskey="{key}" is used {len(same)} times, so the shortcut is unpredictable.', risk='medium')


# ---- AccessLoop's own browser checks (scanner.CUSTOM_RULES) --------------------------------------------------------
FOCUS_STYLE = ('<style data-accessloop="focus-visible">:focus-visible { outline: 3px solid #1a4fd6 !important; '
               'outline-offset: 2px !important; }</style>')


@fixer('al-focus-visible', mode='auto')
def focus_visible(doc, el, f, language, values):
    head = doc.find_first('head')
    if head is None or head.end_start is None or 'data-accessloop="focus-visible"' in doc.source:
        return None
    # One style rule at the end of <head> (after the page's own styles) restores a visible focus ring everywhere.
    return Draft([Edit(head.end_start, head.end_start, FOCUS_STYLE)], (head.start, head.start_end),
                 'Show a clear focus ring on every control that keyboard users can reach.',
                 f'Nothing visibly changed when <{el.tag}> received keyboard focus (the page removes the outline). '
                 'One rule fixes every such control; check it matches your brand colours.', risk='medium')


@fixer('al-text-spacing', mode='auto')
def text_spacing_clip(doc, el, f, language, values):
    if el.tag in {'html', 'body', 'head'}:
        return None
    return Draft(_style_set(doc, el, {'height': 'auto !important', 'max-height': 'none !important',
                                      'overflow': 'visible !important'}), _tag_focus(el),
                 'Let this box grow with its text, so nothing is cut off when users increase spacing.',
                 'With WCAG text-spacing settings applied, the text in this fixed-size box was clipped.', risk='medium')


@fixer('al-reflow', mode='auto')
def reflow(doc, el, f, language, values):
    if el.tag in {'html', 'body', 'head', 'table', 'pre', 'img', 'svg', 'video', 'canvas', 'iframe'}:
        return None
    return Draft(_style_set(doc, el, {'max-width': '100% !important', 'box-sizing': 'border-box',
                                      'overflow-wrap': 'anywhere'}), _tag_focus(el),
                 'Keep this element within the screen width, so small-screen and zoomed users do not scroll sideways.',
                 f'At 320 CSS pixels this element was wider than the screen. {f.description[:120]}', risk='medium')
