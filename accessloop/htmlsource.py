"""Position-aware HTML source model.

The old planner searched the raw text with regular expressions, once per finding, and re-parsed the whole page for
every candidate. That was slow (cubic) and could match text inside comments. This module tokenises the source ONCE,
records exact character offsets for every tag and attribute, and lets fixers express a change as small offset edits.

The tokenizer follows the HTML tokenisation rules that matter for editing: comments, doctype, raw-text elements
(script, style, textarea, title ...), quoted and unquoted attributes, and ">" inside quoted attribute values.
It is NOT a full HTML5 tree builder; the browser stays the authority, and every edit is re-verified by a re-scan.
"""
from __future__ import annotations
import html as html_std
import re
from dataclasses import dataclass, field

VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
# Elements whose content is text, not markup (noscript behaves this way when scripting is on, as in our scanner).
RAW_TEXT = frozenset('script style textarea title xmp iframe noembed noframes noscript plaintext'.split())
FOREIGN = frozenset({'svg', 'math'})
UID_ATTR = 'data-al-uid'

_ATTR = re.compile(r'''[\s/]*(?P<name>[^\s"'<>/=]+)(?:\s*=\s*(?:"(?P<dq>[^"]*)"|'(?P<sq>[^']*)'|(?P<uq>[^\s>]*)))?''')
_NAME_END = re.compile(r'[\s/>]')
_AUTO_CLOSE = {  # opening tag -> open elements it implicitly closes (nearest only)
    'li': {'li'}, 'dt': {'dt', 'dd'}, 'dd': {'dt', 'dd'}, 'tr': {'tr', 'td', 'th'}, 'td': {'td', 'th'}, 'th': {'td', 'th'},
    'option': {'option'}, 'optgroup': {'optgroup', 'option'}, 'thead': {'tbody', 'tfoot', 'tr', 'td', 'th'},
    'tbody': {'thead', 'tbody', 'tfoot', 'tr', 'td', 'th'}, 'tfoot': {'thead', 'tbody', 'tr', 'td', 'th'},
}
_CLOSES_P = frozenset('address article aside blockquote details div dl fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 '
                      'header hr main menu nav ol p pre section table ul'.split())
_SCOPE_STOP = {'li': {'ul', 'ol', 'menu'}, 'dt': {'dl'}, 'dd': {'dl'}, 'tr': {'table', 'thead', 'tbody', 'tfoot'},
               'td': {'tr', 'table'}, 'th': {'tr', 'table'}, 'option': {'select', 'datalist', 'optgroup'},
               'optgroup': {'select'}, 'thead': {'table'}, 'tbody': {'table'}, 'tfoot': {'table'}}


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    text: str


@dataclass
class Attr:
    name: str            # lower-case
    start: int           # span of the whole attribute text in the source
    end: int
    value: str | None    # unescaped; None when written without "=value"
    value_start: int | None = None   # inner span of the value (without quotes)
    value_end: int | None = None
    quote: str = ''


@dataclass(eq=False)
class Element:
    uid: int
    tag: str
    raw_tag: str                      # tag name exactly as written
    start: int                        # '<'
    name_end: int                     # offset right after the tag name
    start_end: int                    # offset right after '>'
    attrs: list[Attr]
    parent: 'Element | None' = None
    children: list['Element'] = field(default_factory=list)
    end_start: int | None = None      # '<' of the end tag, when one exists
    end_end: int | None = None
    self_closed: bool = False
    in_foreign: bool = False

    def get(self, name: str) -> Attr | None:
        name = name.lower()
        for a in self.attrs:
            if a.name == name:
                return a
        return None

    def value(self, name: str) -> str | None:
        a = self.get(name)
        return None if a is None else (a.value if a.value is not None else '')

    @property
    def content(self) -> tuple[int, int] | None:
        """Span of the element's inner source, or None for void/unterminated elements."""
        if self.tag in VOID or self.self_closed or self.end_start is None:
            return None
        return self.start_end, self.end_start


class Doc:
    """Parsed source plus lookup tables. Build once per source version."""

    def __init__(self, source: str):
        self.source = source
        self.elements: list[Element] = []
        self.root_children: list[Element] = []
        self._parse()
        self.by_uid = {e.uid: e for e in self.elements}
        self.ids: dict[str, list[Element]] = {}
        for e in self.elements:
            v = e.value('id')
            if v:
                self.ids.setdefault(v, []).append(e)

    # ---- parsing -----------------------------------------------------------------------------
    def _parse(self) -> None:
        s = self.source
        n = len(s)
        pos = 0
        stack: list[Element] = []
        while pos < n:
            lt = s.find('<', pos)
            if lt < 0:
                break
            nxt = s[lt + 1:lt + 2]
            if s.startswith('<!--', lt):
                if s.startswith('<!-->', lt):
                    pos = lt + 5
                elif s.startswith('<!--->', lt):
                    pos = lt + 6
                else:
                    close = s.find('-->', lt + 4)
                    pos = n if close < 0 else close + 3
                continue
            if nxt in ('!', '?'):
                close = s.find('>', lt + 2)
                pos = n if close < 0 else close + 1
                continue
            if nxt == '/':
                m = re.match(r'</([A-Za-z][^\s/>]*)', s[lt:lt + 80])
                if not m:
                    close = s.find('>', lt + 2)
                    pos = n if close < 0 else close + 1
                    continue
                end = self._tag_end(lt + 2 + len(m.group(1)))
                if end < 0:
                    break
                self._close(stack, m.group(1).lower(), lt, end)
                pos = end
                continue
            if not nxt.isalpha():
                pos = lt + 1
                continue
            m = _NAME_END.search(s, lt + 1)
            name_end = m.start() if m else n
            raw_tag = s[lt + 1:name_end]
            tag = raw_tag.lower()
            attrs, start_end, closed_slash = self._attrs(name_end)
            if start_end < 0:        # unterminated tag at end of input: the browser drops it
                break
            self._implied_close(stack, tag, lt)
            parent = stack[-1] if stack else None
            foreign = bool(parent and (parent.in_foreign or parent.tag in FOREIGN)) or tag in FOREIGN
            el = Element(len(self.elements), tag, raw_tag, lt, name_end, start_end, attrs, parent=parent,
                         self_closed=closed_slash and (foreign or tag in VOID), in_foreign=foreign)
            self.elements.append(el)
            (parent.children if parent else self.root_children).append(el)
            pos = start_end
            if tag in VOID or el.self_closed:
                continue
            # script and style content is never parsed for elements, even inside SVG/MathML: nothing inside is ever edited
            if tag in RAW_TEXT and (not foreign or tag in ('script', 'style')):
                close = re.compile(r'</' + re.escape(tag) + r'(?=[\s/>])', re.I).search(s, start_end)
                el_end = close.start() if close else n
                stack.append(el)
                pos = el_end
                continue
            stack.append(el)
        self._finish(stack)

    def _finish(self, stack: list[Element]) -> None:
        self._pop(stack, 0, len(self.source))

    def _tag_end(self, i: int) -> int:
        """Offset just after the '>' that closes a tag whose name ends at i (quote-aware); -1 if unterminated."""
        s, n = self.source, len(self.source)
        while i < n:
            if s[i] == '>':
                return i + 1
            if s[i] in '"\'' and s[i - 1:i] == '=':
                q = s.find(s[i], i + 1)
                if q < 0:
                    return -1
                i = q + 1
                continue
            i += 1
        return -1

    def _attrs(self, i: int) -> tuple[list[Attr], int, bool]:
        s, n = self.source, len(self.source)
        attrs: list[Attr] = []
        slash = False
        while i < n:
            while i < n and s[i] in ' \t\r\n\f':
                i += 1
            if i >= n:
                return attrs, -1, False
            if s[i] == '>':
                return attrs, i + 1, slash
            if s[i] == '/':
                slash = s[i + 1:i + 2] == '>'
                i += 1
                continue
            slash = False
            m = _ATTR.match(s, i)
            if not m or m.end() == i:
                i += 1
                continue
            name = m.group('name')
            a_start = m.start('name')
            if m.group('dq') is not None:
                raw, vs, q = m.group('dq'), m.start('dq'), '"'
            elif m.group('sq') is not None:
                raw, vs, q = m.group('sq'), m.start('sq'), "'"
            elif m.group('uq') is not None:
                raw, vs, q = m.group('uq'), m.start('uq'), ''
            else:
                raw, vs, q = None, None, ''
            end = m.end()
            if q and (end > n or s[end - 1:end] != q):
                return attrs, -1, False
            attrs.append(Attr(name.lower(), a_start, end, None if raw is None else html_std.unescape(raw),
                              vs, None if vs is None else vs + len(raw), q))
            i = end
        return attrs, -1, False

    @staticmethod
    def _pop(stack: list[Element], k: int, at: int) -> None:
        for el in stack[k:]:
            if el.end_start is None:
                el.end_start = el.end_end = at     # implied end tag: the element ends where the next tag begins
        del stack[k:]

    @classmethod
    def _implied_close(cls, stack: list[Element], tag: str, at: int) -> None:
        if tag in _CLOSES_P:
            for k in range(len(stack) - 1, -1, -1):
                if stack[k].tag == 'p':
                    cls._pop(stack, k, at)
                    break
                if stack[k].tag in {'div', 'td', 'th', 'li', 'body', 'section', 'article', 'main', 'form', 'table'}:
                    break
        targets = _AUTO_CLOSE.get(tag)
        if targets:
            stops = _SCOPE_STOP.get(tag, set())
            for k in range(len(stack) - 1, -1, -1):
                if stack[k].tag in targets:
                    cls._pop(stack, k, at)
                    break
                if stack[k].tag in stops:
                    break

    @classmethod
    def _close(cls, stack: list[Element], tag: str, start: int, end: int) -> None:
        for k in range(len(stack) - 1, -1, -1):
            if stack[k].tag == tag:
                cls._pop(stack, k + 1, start)          # anything still open inside is implicitly closed here
                stack[k].end_start, stack[k].end_end = start, end
                del stack[k:]
                return

    # ---- queries -----------------------------------------------------------------------------
    def text_of(self, el: Element) -> str:
        span = el.content
        if span is None:
            return ''
        raw = self.source[span[0]:span[1]]
        raw = re.sub(r'<!--.*?-->', '', raw, flags=re.S)
        raw = re.sub(r'<[^>]*>', '', raw)
        return re.sub(r'\s+', ' ', html_std.unescape(raw)).strip()

    def previous_element_sibling(self, el: Element) -> Element | None:
        """Previous sibling element with only whitespace or comments between it and `el`."""
        siblings = el.parent.children if el.parent else self.root_children
        i = siblings.index(el)
        if i == 0:
            return None
        prev = siblings[i - 1]
        end = prev.end_end if prev.end_end is not None else (prev.start_end if prev.tag in VOID or prev.self_closed else None)
        if end is None:
            return None
        gap = re.sub(r'<!--.*?-->', '', self.source[end:el.start], flags=re.S)
        return None if gap.strip() else prev

    def unique_id(self, el: Element) -> str | None:
        v = el.value('id')
        return v if v and len(self.ids.get(v, [])) == 1 and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]*', v) else None

    def resolve_selector_id(self, selector: str) -> Element | None:
        """Legacy mapping for findings without a uid: a plain '#id' selector that names exactly one element."""
        m = re.fullmatch(r'#([A-Za-z][A-Za-z0-9_-]*)', selector.strip())
        if m:
            found = self.ids.get(m.group(1), [])
            return found[0] if len(found) == 1 else None
        if selector.strip().lower() == 'html':
            return next((e for e in self.elements if e.tag == 'html'), None)
        return None

    def find_first(self, tag: str) -> Element | None:
        return next((e for e in self.elements if e.tag == tag), None)

    # ---- edit helpers ------------------------------------------------------------------------
    def set_attr(self, el: Element, name: str, value: str) -> list[Edit]:
        rendered = f'{name}="{html_std.escape(value, quote=True)}"'
        a = el.get(name)
        if a is not None:
            return [Edit(a.start, a.end, rendered)]
        pos = el.start_end - 1                       # the '>'
        if self.source[pos - 1:pos] == '/' and (el.self_closed or el.tag in VOID):
            pos -= 1                                  # keep a trailing "/>" intact
            while pos > el.name_end and self.source[pos - 1] in ' \t\r\n':
                pos -= 1
        return [Edit(pos, pos, ' ' + rendered)]

    def remove_attr(self, el: Element, name: str) -> list[Edit]:
        a = el.get(name)
        if a is None:
            return []
        start = a.start
        while start > el.name_end and self.source[start - 1] in ' \t\r\n':
            start -= 1
        return [Edit(start, a.end, '')]

    def remove_attr_value_tokens(self, el: Element, name: str, tokens: set[str]) -> list[Edit]:
        a = el.get(name)
        if a is None or a.value is None:
            return []
        kept = [t for t in a.value.split() if t.lower() not in tokens]
        return self.remove_attr(el, name) if not kept else self.set_attr(el, name, ' '.join(kept))


def apply_edits(source: str, edits: list[Edit]) -> str:
    ordered = sorted(edits, key=lambda e: (e.start, e.end))
    for a, b in zip(ordered, ordered[1:]):
        if a.end > b.start:
            raise ValueError('Overlapping edits.')
    out = source
    for e in reversed(ordered):
        out = out[:e.start] + e.text + out[e.end:]
    return out


def instrument(doc: Doc) -> str:
    """Source copy with data-al-uid="N" on every start tag, so axe findings map to exact source elements."""
    edits = [Edit(e.name_end, e.name_end, f' {UID_ATTR}="{e.uid}"') for e in doc.elements]
    return apply_edits(doc.source, edits)


def shifted_span(span: tuple[int, int], edits: list[Edit]) -> tuple[int, int]:
    """Where an original [start, end) span sits after the edits (edits inside it grow or shrink it)."""
    start, end = span
    new_start, new_end = start, end
    for e in sorted(edits, key=lambda x: x.start):
        delta = len(e.text) - (e.end - e.start)
        if e.end <= start:
            new_start += delta
            new_end += delta
        elif e.start < end or e.start == e.end == end:   # insertions inside, or right at the end of, the span
            new_end += delta
    return new_start, new_end


# ---- structural helpers (used by fixers) ----------------------------------------------------------------
def extent_end(el: Element) -> int:
    """Offset right after the element's last character (end tag, or start tag for void/unterminated elements)."""
    if el.end_end is not None:
        return el.end_end
    return el.start_end


def descendants(doc: Doc, el: Element) -> list[Element]:
    end = extent_end(el)
    return [e for e in doc.elements if el.start < e.start < end]


def has_real_end_tag(doc: Doc, el: Element) -> bool:
    return el.end_start is not None and el.end_end is not None and doc.source[el.end_start:el.end_start + 2] == '</'


def rename_tag(doc: Doc, el: Element, new: str) -> list[Edit]:
    """Change <old ...>...</old> to <new ...>...</new>, keeping every attribute and all content."""
    edits = [Edit(el.start + 1, el.name_end, new)]
    if has_real_end_tag(doc, el):
        edits.append(Edit(el.end_start + 2, el.end_start + 2 + len(el.raw_tag), new))
    return edits


def wrap(first: Element, last: Element, open_tag: str, close_tag: str) -> list[Edit]:
    """Insert open_tag before `first` and close_tag after `last` (siblings, in document order)."""
    return [Edit(first.start, first.start, open_tag), Edit(extent_end(last), extent_end(last), close_tag)]


ACTIVE_URL = re.compile(r'^\s*(javascript|vbscript|data:text/html|data:application|data:image/svg)', re.I)
URL_ATTR_NAMES = frozenset({'href', 'src', 'action', 'formaction', 'data', 'poster', 'xlink:href', 'background'})
CSP_META = ('<meta http-equiv="Content-Security-Policy" content="script-src \'none\'; object-src \'none\'; '
            'frame-src \'none\'">')


def scan_copy(doc: Doc, base_href: str | None = None) -> str:
    """The copy of the page that the browser scans (never written to disk, never the user's file):

    * every start tag gets data-al-uid="N" so each axe finding maps to an exact source element;
    * nothing on the page can run: <script>, <base>, inline event handlers, srcdoc and active URLs are removed from
      this copy, and a Content-Security-Policy that forbids scripts is put first;
    * optionally a <base> pointing at the local-assets origin, so the page's own style sheets and images load.
    """
    removed: list[tuple[int, int]] = []
    edits: list[Edit] = []
    for e in doc.elements:
        if any(a <= e.start < b for a, b in removed):
            continue
        if e.tag in {'script', 'base'}:
            span = (e.start, extent_end(e))
            removed.append(span)
            edits.append(Edit(span[0], span[1], ''))
            continue
        edits.append(Edit(e.name_end, e.name_end, f' {UID_ATTR}="{e.uid}"'))
        for a in e.attrs:
            if a.name.startswith('on') or a.name == 'srcdoc' or \
                    (a.name in URL_ATTR_NAMES and a.value is not None and ACTIVE_URL.match(a.value)):
                edits.append(Edit(a.start, a.end, ''))
    head = doc.find_first('head')
    prefix = CSP_META + (f'<base href="{html_std.escape(base_href, quote=True)}">' if base_href else '')
    if head is not None and head.start_end is not None and not any(a <= head.start < b for a, b in removed):
        edits.append(Edit(head.start_end, head.start_end, prefix))
    else:
        html_el = doc.find_first('html')
        at = html_el.start_end if html_el is not None else 0
        edits.append(Edit(at, at, prefix))
    return apply_edits(doc.source, edits)
