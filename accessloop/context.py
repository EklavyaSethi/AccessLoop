"""Where is this on the page? Context for one proposed fix, so a reviewer can judge a one-line change in a 1,000-line file.

Three views, all computed from the page itself (nothing guessed, nothing sent anywhere):
  * a plain-English description: what the element is, its form, section heading and landmark;
  * a breadcrumb of the meaningful containers it sits in (landmarks, forms, fieldsets with their legends, tables with
    their captions, dialogs, lists);
  * the surrounding source code with line numbers, the lines the fix touches highlighted;
and, rendered on demand by the scanner, a cropped picture of the element on the page with a red outline.
"""
from __future__ import annotations
import re

from .htmlsource import Doc, Element, extent_end

LANDMARK_TAGS = {'header': 'page header', 'nav': 'navigation', 'main': 'main content', 'aside': 'sidebar',
                 'footer': 'page footer', 'form': 'form', 'section': 'section', 'article': 'article', 'dialog': 'dialog',
                 'fieldset': 'group', 'table': 'table', 'ul': 'list', 'ol': 'list', 'details': 'expandable section'}
LANDMARK_ROLES = {'banner': 'page header', 'navigation': 'navigation', 'main': 'main content', 'complementary': 'sidebar',
                  'contentinfo': 'page footer', 'form': 'form', 'region': 'section', 'dialog': 'dialog', 'search': 'search',
                  'tablist': 'tabs', 'menu': 'menu', 'list': 'list', 'group': 'group', 'radiogroup': 'option group'}
KIND = {'input': 'field', 'select': 'drop-down', 'textarea': 'text box', 'button': 'button', 'a': 'link', 'img': 'image',
        'svg': 'graphic', 'table': 'table', 'th': 'table header cell', 'td': 'table cell', 'label': 'label',
        'html': 'whole page', 'head': 'page settings', 'title': 'page title', 'meta': 'page setting',
        'iframe': 'embedded frame', 'video': 'video', 'audio': 'audio', 'h1': 'heading', 'h2': 'heading',
        'h3': 'heading', 'h4': 'heading', 'h5': 'heading', 'h6': 'heading', 'li': 'list item', 'ul': 'list',
        'ol': 'list', 'form': 'form', 'main': 'main area', 'nav': 'navigation', 'area': 'image-map area',
        'object': 'embedded object', 'summary': 'expandable heading', 'span': 'piece of text', 'div': 'page area', 'p': 'paragraph', 'section': 'section'}
INVISIBLE = {'html', 'head', 'title', 'meta', 'link', 'style', 'script', 'base'}


def _short(text: str, n: int = 60) -> str:
    text = re.sub(r'\s+', ' ', text or '').strip()
    return text if len(text) <= n else text[: n - 1] + '…'


def _name_of(doc: Doc, el: Element) -> str:
    """A human name for a container: legend, caption, aria-label, first heading inside, or id."""
    if el.value('aria-label'):
        return el.value('aria-label') or ''
    for child in el.children:
        if child.tag in ('legend', 'caption', 'summary') or re.fullmatch(r'h[1-6]', child.tag):
            t = doc.text_of(child)
            if t:
                return t
    labelled = el.value('aria-labelledby')
    if labelled:
        found = [doc.text_of(x) for i in labelled.split() for x in doc.ids.get(i, [])]
        if any(found):
            return ' '.join(f for f in found if f)
    return el.value('name') or el.value('id') or ''


def _kind(el: Element) -> str:
    kind = KIND.get(el.tag, f'<{el.tag}> element')
    if el.tag == 'input':
        typ = (el.value('type') or 'text').lower()
        kind = {'submit': 'submit button', 'button': 'button', 'image': 'image button', 'checkbox': 'checkbox',
                'radio': 'option button', 'hidden': 'hidden field', 'reset': 'reset button'}.get(typ, f'{typ} field')
    role = (el.value('role') or '').split()
    if role:
        kind = f'{kind} (role "{role[0]}")'
    return kind


def _identity(doc: Doc, el: Element) -> str:
    """How a person would recognise the element: its visible text, label, file name, name or id."""
    text = _short(doc.text_of(el), 50)
    if el.tag == 'img' and el.value('src'):
        return f'image file "{el.value("src").split("?")[0].rsplit("/", 1)[-1]}"'
    if el.tag == 'a' and el.value('href') and not text:
        return f'linking to "{_short(el.value("href"), 40)}"'
    if el.tag in ('input', 'select', 'textarea'):
        own = el.value('id')
        label = next((doc.text_of(x) for x in doc.elements if x.tag == 'label' and own and x.value('for') == own), '')
        if not label and el.parent is not None and el.parent.tag == 'label':
            label = doc.text_of(el.parent)
        if not label:
            prev = doc.previous_element_sibling(el)
            if prev is not None and prev.tag == 'label':
                label = doc.text_of(prev) + ' (not linked yet)'
        bits = [f'next to the text "{_short(label, 40)}"'] if label else []
        if el.value('name'):
            bits.append(f'name "{el.value("name")}"')
        if el.value('placeholder'):
            bits.append(f'placeholder "{_short(el.value("placeholder"), 30)}"')
        return ', '.join(bits) or (f'id "{own}"' if own else '')
    if text:
        return f'"{text}"'
    return f'id "{el.value("id")}"' if el.value('id') else ''


def _containers(doc: Doc, el: Element) -> list[tuple[str, str]]:
    out = []
    p = el.parent
    while p is not None:
        roles = (p.value('role') or '').split()
        label = LANDMARK_ROLES.get(roles[0]) if roles else LANDMARK_TAGS.get(p.tag)
        if label and not (p.tag == 'section' and not _name_of(doc, p)):
            out.append((label, _short(_name_of(doc, p), 40)))
        p = p.parent
    return list(reversed(out))


def _section_heading(doc: Doc, el: Element) -> str:
    best = ''
    for h in doc.elements:
        if h.start >= el.start:
            break
        if re.fullmatch(r'h[1-6]', h.tag) or (h.value('role') or '') == 'heading':
            t = doc.text_of(h)
            if t:
                best = f'{t} ({h.tag})' if h.tag.startswith('h') else t
    return _short(best, 70)


def line_of(doc: Doc, offset: int) -> int:
    return doc.source.count('\n', 0, offset) + 1


_DOCS: dict = {}


def _doc(html: str) -> Doc:
    """Parse once per page version: a review screen asks for the context of every proposal on the same page."""
    key = hash(html)
    doc = _DOCS.get(key)
    if doc is None or doc.source != html:
        if len(_DOCS) > 8:
            _DOCS.clear()
        doc = _DOCS[key] = Doc(html)
    return doc


def describe(html: str, uid: int | None, edits=()) -> dict:
    """Context for the element with this uid (and the lines the edits touch)."""
    doc = _doc(html)
    el = doc.by_uid.get(uid) if uid is not None else None
    if el is None:
        return {'found': False, 'sentence': 'This fix applies to the page as a whole.', 'breadcrumb': [], 'lines': [],
                'section': '', 'visible': False}
    kind = _kind(el)
    who = _identity(doc, el)
    containers = _containers(doc, el)
    section = _section_heading(doc, el)
    where = []
    for label, name in reversed(containers):
        if label in ('form', 'group', 'table', 'dialog', 'main content', 'page header', 'page footer', 'navigation', 'sidebar'):
            where.append(f'in the {label}' + (f' "{name}"' if name else ''))
        if len(where) == 2:
            break
    article = 'An' if kind[:1].lower() in 'aeiou' else 'A'
    sentence = f'{article} {kind}' + (f' ({who})' if who else '')
    if el.tag in INVISIBLE:
        sentence = {'html': 'The page itself (the <html> element at the top of the file).',
                    'title': 'The page title shown in the browser tab.',
                    'meta': 'A page setting in the <head> (not visible on screen).'}.get(el.tag, f'A <{el.tag}> in the page settings.')
    else:
        if where:
            sentence += ' ' + ', '.join(where)
        if section:
            sentence += f', under the heading "{section}"'
        sentence += '.'
    # lines: the element (or the edits) plus context
    starts = [e.start for e in edits] or [el.start]
    ends = [max(e.end, e.start) for e in edits] or [min(extent_end(el), el.start_end + 400)]
    first, last = line_of(doc, min(starts)), line_of(doc, max(ends))
    lines = doc.source.split('\n')
    lo, hi = max(1, first - 6), min(len(lines), last + 6)
    if hi - lo > 40:                                    # very large elements: show the start and the end
        hi = lo + 40
    view = [{'n': n, 'text': lines[n - 1][:220] + ('…' if len(lines[n - 1]) > 220 else ''), 'changed': first <= n <= last}
            for n in range(lo, hi + 1)]
    crumbs = ['page'] + [f'{label} "{name}"' if name else label for label, name in containers]
    crumbs.append(kind.split(' (')[0])
    return {'found': True, 'sentence': sentence, 'breadcrumb': crumbs, 'section': section, 'lines': view,
            'first_line': first, 'last_line': last, 'total_lines': len(lines), 'visible': el.tag not in INVISIBLE,
            'uid': uid}
