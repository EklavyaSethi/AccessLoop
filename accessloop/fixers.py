"""Fix templates. Each fixer turns one axe finding on one source element into small offset edits.

Three kinds of fix, all human-approved and re-verified by a re-scan:
  auto   - everything needed is already on the page (a visible label to link, a hidden-but-visible button text ...)
  input  - needs words only a person knows (alt text, a link name, a title). The reviewer types them; the tool never guesses.
  mixed  - auto when the page gives clear evidence, otherwise it asks for input.
No fixer ever writes script, and none uses model output as code.
"""
from __future__ import annotations
import html as html_std
import re
from dataclasses import dataclass, field
from typing import Callable

from .htmlsource import Doc, Edit, Element

LANGUAGE_OPTIONS = [
    ('en', 'English'), ('en-IN', 'English (India)'), ('hi', 'Hindi'), ('bn', 'Bengali'), ('ta', 'Tamil'),
    ('te', 'Telugu'), ('mr', 'Marathi'), ('gu', 'Gujarati'), ('kn', 'Kannada'), ('ml', 'Malayalam'),
    ('pa', 'Punjabi'), ('ur', 'Urdu'), ('fr', 'French'), ('es', 'Spanish'), ('de', 'German'),
]
AUTOCOMPLETE_OPTIONS = [
    ('name', 'Full name'), ('given-name', 'First name'), ('family-name', 'Last name'), ('email', 'Email'),
    ('tel', 'Phone number'), ('username', 'Username / customer ID'), ('current-password', 'Current password'),
    ('new-password', 'New password'), ('one-time-code', 'One-time code (OTP)'), ('bday', 'Date of birth'),
    ('street-address', 'Street address'), ('postal-code', 'Postal code'), ('cc-name', 'Name on card'),
    ('cc-number', 'Card number'), ('cc-exp', 'Card expiry'), ('organization', 'Organisation'), ('off', 'Turn autocomplete off'),
]


class FixInputError(ValueError):
    """The reviewer's typed value is missing or unsafe."""


@dataclass
class Draft:
    edits: list[Edit] = field(default_factory=list)
    focus: tuple[int, int] = (0, 0)
    explanation: str = ''
    evidence: str = ''
    mode: str = 'auto'                 # 'auto' or 'input'
    fields: tuple = ()                 # input mode: what to ask the reviewer
    risk: str = 'low'                  # low | medium
    preview: str = ''                  # input mode: the change shown before the reviewer types anything


Fixer = Callable[[Doc, Element, object, str, 'dict | None'], 'Draft | None']
FIXERS: dict[str, Fixer] = {}
MODES: dict[str, str] = {}


def fixer(*rules: str, mode: str):
    def wrap(fn: Fixer) -> Fixer:
        for r in rules:
            FIXERS[r] = fn
            MODES[r] = mode
        return fn
    return wrap


# ---- helpers ---------------------------------------------------------------------------------------------
def clean_text(value: object, low: int = 1, high: int = 150, label: str = 'The text') -> str:
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    if re.search(r'[\x00-\x1f\x7f<>]', text):
        raise FixInputError(f'{label} cannot contain angle brackets or control characters.')
    if len(text) < low:
        raise FixInputError(f'{label} is required.')
    if len(text) > high:
        raise FixInputError(f'{label} must be {high} characters or fewer.')
    return text


def _tag_focus(el: Element) -> tuple[int, int]:
    return el.start, el.start_end


def _text_field(name: str, label: str, help: str = '', required: bool = True) -> dict:
    return {'name': name, 'label': label, 'kind': 'text', 'help': help, 'required': required, 'max': 150}


def _ask(el: Element, attr: str, fld: dict, why: str, evidence: str, tag_word: str = '') -> Draft:
    return Draft(focus=_tag_focus(el), explanation=why, evidence=evidence, mode='input', fields=(fld,),
                 preview=f'{attr}="…"')


def _hidden_text_spans(doc: Doc, el: Element) -> list[Element]:
    """The child spans that hide all of the button's visible text with aria-hidden="true" (empty list if not that case)."""
    kids = el.children
    if not kids or len(kids) > 4:
        return []
    for child in kids:
        h = child.get('aria-hidden')
        if child.tag != 'span' or h is None or (h.value or '').strip().lower() != 'true' or child.end_start is None \
                or child.children:
            return []
    joined = ''.join(doc.text_of(c) for c in kids)
    outside = doc.text_of(el).replace(' ', '') != joined.replace(' ', '')
    if not 2 <= len(joined) <= 80 or outside:
        return []
    return list(kids)


# ---- page language ---------------------------------------------------------------------------------------
@fixer('html-has-lang', mode='auto')
def html_has_lang(doc, el, f, language, values):
    el = el if el.tag == 'html' else doc.find_first('html')
    if el is None or not re.fullmatch(r'[a-z]{2}(?:-[A-Z]{2})?', language):
        return None
    current = el.get('lang')
    if current is not None and (current.value or '').strip():
        return None
    return Draft(doc.set_attr(el, 'lang', language), _tag_focus(el), 'Declare the document language for screen readers.',
                 f'Language explicitly selected by reviewer: {language}')


@fixer('html-lang-valid', 'valid-lang', mode='input')
def lang_valid(doc, el, f, language, values):
    fld = {'name': 'lang', 'label': 'Language of this part of the page', 'kind': 'select', 'required': True,
           'options': LANGUAGE_OPTIONS}
    shown = el.value('lang')
    if values is None:
        return Draft(focus=_tag_focus(el), explanation='The lang value is not a valid language code. Choose the right one.',
                     evidence=f'Current value: "{shown}"', mode='input', fields=(fld,), preview='lang="…"')
    code = str(values.get('lang', ''))
    if code not in {c for c, _ in LANGUAGE_OPTIONS}:
        raise FixInputError('Choose a language from the list.')
    return Draft(doc.set_attr(el, 'lang', code), _tag_focus(el), 'Replace the invalid language code with the one you chose.',
                 f'Replaced "{shown}" with "{code}"')


@fixer('html-xml-lang-mismatch', mode='auto')
def xml_lang_mismatch(doc, el, f, language, values):
    el = el if el.tag == 'html' else doc.find_first('html')
    lang, xml = (el.value('lang') or '').strip() if el else '', (el.value('xml:lang') or '').strip() if el else ''
    if not el or not lang or not xml:
        return None
    return Draft(doc.set_attr(el, 'xml:lang', lang), _tag_focus(el), 'Make xml:lang match the lang attribute.',
                 f'lang="{lang}" but xml:lang="{xml}"')


# ---- form labels -----------------------------------------------------------------------------------------
def _slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:30] or 'field'


@fixer('label', 'select-name', mode='mixed')
def form_label(doc, el, f, language, values):
    if el.tag not in {'input', 'textarea', 'select'}:
        return None
    prev = doc.previous_element_sibling(el)
    if values is None and prev is not None and prev.tag == 'label' and prev.get('for') is None and prev.end_start is not None:
        text = doc.text_of(prev)
        own_id = el.value('id')
        id_ok = (own_id is None or own_id == '') or doc.unique_id(el) is not None
        if 2 <= len(text) <= 80 and id_ok and not any(c.tag in {'input', 'select', 'textarea'} for c in prev.children):
            edits, target_id = [], doc.unique_id(el)
            if target_id is None:
                base, n, target_id = 'al-' + _slug(text), 1, 'al-' + _slug(text)
                while target_id in doc.ids:
                    n += 1
                    target_id = f'{base}-{n}'
                edits += doc.set_attr(el, 'id', target_id)
            edits += doc.set_attr(prev, 'for', target_id)
            note = '' if doc.unique_id(el) else f' The field had no id, so the id "{target_id}" is added.'
            return Draft(edits, (prev.start, el.start_end), 'Associate the existing visible label with the field.',
                         f'Adjacent label text: "{text}"; field id: {target_id}.{note}')
    return _aria_label(doc, el, values, 'This field has no visible label next to it that can be linked safely. '
                       'Type the name a screen-reader user should hear.', 'Field name')


# ---- accessible names by typed text ----------------------------------------------------------------------
def _aria_label(doc: Doc, el: Element, values, why: str, label: str, attr: str = 'aria-label') -> Draft | None:
    fld = _text_field('text', label, 'Short and specific, for example "Search" or "Mobile number".')
    if values is None:
        return Draft(focus=_tag_focus(el), explanation=why, evidence=f'<{el.tag}> has no accessible name.', mode='input',
                     fields=(fld,), preview=f'{attr}="…"')
    text = clean_text(values.get('text'), 1, 150, label)
    return Draft(doc.set_attr(el, attr, text), _tag_focus(el), f'Add the accessible name you typed ({attr}).',
                 f'Reviewer-provided {label.lower()}: "{text}"')


@fixer('button-name', mode='mixed')
def button_name(doc, el, f, language, values):
    if values is None and el.tag == 'button':
        spans = _hidden_text_spans(doc, el)
        if spans:
            text = doc.text_of(el)
            return Draft([e for c in spans for e in doc.remove_attr(c, 'aria-hidden')], (el.start_end, el.end_start),
                         'Expose the button’s existing visible text to assistive technology.',
                         f'Button already shows "{text}" but incorrectly hides it from the accessibility tree.')
    return _aria_label(doc, el, values, 'The button has no text a screen reader can read. Type what it does.', 'Button name')


@fixer('link-name', 'input-button-name', 'summary-name', 'aria-command-name', 'aria-input-field-name', 'aria-meter-name',
       'aria-progressbar-name', 'aria-tab-name', 'aria-toggle-field-name', 'aria-tooltip-name', 'aria-treeitem-name',
       'aria-dialog-name', 'role-img-alt', 'svg-img-alt', mode='input')
def accessible_name(doc, el, f, language, values):
    label = {'link-name': 'Link name', 'input-button-name': 'Button name', 'role-img-alt': 'Image description',
             'svg-img-alt': 'Image description'}.get(f.rule_id, 'Accessible name')
    return _aria_label(doc, el, values, f'This {el.tag} has no accessible name. Type what it is or does.', label)


@fixer('image-alt', mode='input')
def image_alt(doc, el, f, language, values):
    if el.tag != 'img':
        return None
    flds = (_text_field('alt', 'Alternative text', 'Describe what the image shows or says, not "image of".', required=False),
            {'name': 'decorative', 'label': 'This image is decorative (adds no information)', 'kind': 'checkbox', 'required': False})
    if values is None:
        return Draft(focus=_tag_focus(el), explanation='Images need a text alternative, or must be marked decorative.',
                     evidence=f'<img src="{html_std.escape(el.value("src") or "", quote=True)[:80]}"> has no alt attribute.',
                     mode='input', fields=flds, preview='alt="…"')
    if values.get('decorative') in (True, 'true', 'on', '1', 1):
        return Draft(doc.set_attr(el, 'alt', ''), _tag_focus(el), 'Mark the image as decorative with an empty alt.', 'Reviewer marked the image decorative.')
    text = clean_text(values.get('alt'), 1, 150, 'Alternative text')
    return Draft(doc.set_attr(el, 'alt', text), _tag_focus(el), 'Add the alternative text you typed.', f'Reviewer-provided alt text: "{text}"')


@fixer('input-image-alt', 'area-alt', mode='input')
def alt_attribute(doc, el, f, language, values):
    return _aria_label(doc, el, values, 'This control needs a text alternative. Type what it does.', 'Alternative text', attr='alt')


@fixer('frame-title', mode='input')
def frame_title(doc, el, f, language, values):
    return _aria_label(doc, el, values, 'Frames need a title that says what they contain.', 'Frame title', attr='title')


@fixer('document-title', mode='input')
def document_title(doc, el, f, language, values):
    title = doc.find_first('title')
    fld = _text_field('title', 'Page title', 'For example "Open an account | Meridian Bank".')
    head, html = doc.find_first('head'), doc.find_first('html')
    anchor = title or head or html
    if anchor is None:
        return None
    if values is None:
        return Draft(focus=_tag_focus(anchor), explanation='Every page needs a descriptive title. Type one.',
                     evidence='The page has no title text.', mode='input', fields=(fld,), preview='<title>…</title>')
    text = clean_text(values.get('title'), 3, 150, 'Page title')
    escaped = html_std.escape(text, quote=False)
    if title is not None and title.content is not None:
        edits = [Edit(title.start_end, title.end_start, escaped)]
    elif head is not None:
        edits = [Edit(head.start_end, head.start_end, f'<title>{escaped}</title>')]
    else:
        edits = [Edit(html.start_end, html.start_end, f'<head><title>{escaped}</title></head>')]
    return Draft(edits, _tag_focus(anchor), 'Add the page title you typed.', f'Reviewer-provided title: "{text}"')


@fixer('autocomplete-valid', mode='input')
def autocomplete_valid(doc, el, f, language, values):
    fld = {'name': 'token', 'label': 'What does this field collect?', 'kind': 'select', 'required': True,
           'options': AUTOCOMPLETE_OPTIONS}
    if values is None:
        return Draft(focus=_tag_focus(el), explanation='The autocomplete value is not a valid token. Pick the right one.',
                     evidence=f'Current value: "{el.value("autocomplete")}"', mode='input', fields=(fld,), preview='autocomplete="…"')
    token = str(values.get('token', ''))
    if token not in {c for c, _ in AUTOCOMPLETE_OPTIONS}:
        raise FixInputError('Choose an option from the list.')
    return Draft(doc.set_attr(el, 'autocomplete', token), _tag_focus(el), 'Use a valid autocomplete token.', f'Chosen token: "{token}"')


# ---- mechanical fixes -------------------------------------------------------------------------------------
@fixer('meta-viewport', 'meta-viewport-large', mode='auto')
def meta_viewport(doc, el, f, language, values):
    if el.tag != 'meta':
        return None
    parts = [p.strip() for p in re.split(r'[,;]', el.value('content') or '') if p.strip()]
    keep, removed = [], []
    for part in parts:
        key, _, val = part.partition('=')
        key, val = key.strip().lower(), val.strip().lower()
        bad = key == 'user-scalable' and val in {'no', '0'}
        if key == 'maximum-scale':
            try:
                bad = float(val) < 5
            except ValueError:
                bad = False
        (removed if bad else keep).append(part)
    if not removed:
        return None
    new = ', '.join(keep) or 'width=device-width, initial-scale=1'
    return Draft(doc.set_attr(el, 'content', new), _tag_focus(el), 'Allow users to zoom the page.',
                 'Removed: ' + ', '.join(removed))


@fixer('aria-hidden-body', mode='auto')
def aria_hidden_body(doc, el, f, language, values):
    if el.tag != 'body' or el.get('aria-hidden') is None:
        return None
    return Draft(doc.remove_attr(el, 'aria-hidden'), _tag_focus(el), 'Stop hiding the whole page from assistive technology.',
                 '<body aria-hidden> makes the entire page invisible to screen readers.')


@fixer('scrollable-region-focusable', mode='auto')
def scrollable_focusable(doc, el, f, language, values):
    if el.get('tabindex') is not None:
        return None
    return Draft(doc.set_attr(el, 'tabindex', '0'), _tag_focus(el), 'Make the scrollable area reachable with the keyboard.',
                 'The region scrolls but cannot receive keyboard focus.', risk='low')


@fixer('tabindex', mode='auto')
def positive_tabindex(doc, el, f, language, values):
    try:
        value = int((el.value('tabindex') or '').strip())
    except ValueError:
        return None
    if value <= 0:
        return None
    return Draft(doc.set_attr(el, 'tabindex', '0'), _tag_focus(el), 'Use the natural tab order instead of a positive tabindex.',
                 f'tabindex="{value}" changes the keyboard order unpredictably.', risk='medium')


@fixer('blink', 'marquee', mode='auto')
def moving_text(doc, el, f, language, values):
    new = 'span' if el.tag == 'blink' else 'div'
    edits = [Edit(el.start + 1, el.name_end, new)]
    if el.end_start is not None and doc.source[el.end_start:el.end_start + 2] == '</':
        edits.append(Edit(el.end_start + 2, el.end_start + 2 + len(el.raw_tag), new))
    return Draft(edits, _tag_focus(el), f'Replace the moving <{el.tag}> element with a static <{new}>.',
                 f'<{el.tag}> content moves or flashes and cannot be paused.', risk='medium')


def _bad_tokens(f) -> set[str]:
    out: set[str] = set()
    for value in (f.data or {}).values():
        if isinstance(value, dict):            # e.g. {"messageKey": "singular", "values": ['aria-checked="true"']}
            value = value.get('values')
        if isinstance(value, list):
            out |= {str(x) for x in value if isinstance(x, str)}
    return out


@fixer('aria-roles', mode='auto')
def aria_roles(doc, el, f, language, values):
    bad = {t.lower() for t in _bad_tokens(f)}
    a = el.get('role')
    if not a or not bad or not ({t.lower() for t in (a.value or '').split()} & bad):
        return None
    return Draft(doc.remove_attr_value_tokens(el, 'role', bad), _tag_focus(el), 'Remove the role value that does not exist.',
                 'Invalid role: ' + ', '.join(sorted(bad)), risk='medium')


@fixer('aria-valid-attr', 'aria-allowed-attr', mode='auto')
def aria_attrs(doc, el, f, language, values):
    names = {t.split('=')[0].strip().lower() for t in _bad_tokens(f)}
    present = [n for n in names if n.startswith('aria-') and el.get(n) is not None]
    if not present:
        return None
    edits: list[Edit] = []
    for n in sorted(present):
        edits += doc.remove_attr(el, n)
    return Draft(edits, _tag_focus(el), 'Remove ARIA attributes that are invalid or not allowed on this element.',
                 'Removed: ' + ', '.join(sorted(present)), risk='medium')


# ---- colour contrast ---------------------------------------------------------------------------------------
def _rgb(hex_color: str) -> tuple[int, int, int] | None:
    m = re.fullmatch(r'#([0-9a-fA-F]{6})', hex_color.strip())
    if not m:
        return None
    v = m.group(1)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _lum(rgb: tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def nearest_passing(fg: tuple[int, int, int], bg: tuple[int, int, int], needed: float) -> tuple[int, int, int] | None:
    """Blend the text colour towards black or white (whichever the background allows) until the ratio is met."""
    target = (0, 0, 0) if _lum(fg) <= _lum(bg) else (255, 255, 255)
    for step in range(0, 101):
        t = step / 100
        cand = tuple(round(fg[i] + (target[i] - fg[i]) * t) for i in range(3))
        if contrast(cand, bg) >= needed + 0.05:
            return cand  # type: ignore[return-value]
    return None


def _set_style_decl(doc: Doc, el: Element, prop: str, value: str) -> list[Edit]:
    style = el.get('style')
    if style is not None and style.value_start is not None:
        decl = style.value or ''
        if re.search(rf'(^|;)\s*{prop}\s*:', decl, re.I):
            decl = re.sub(rf'((?:^|;)\s*){prop}\s*:[^;]*', lambda m: f'{m.group(1)}{prop}: {value}', decl, count=1, flags=re.I)
        else:
            decl = decl.rstrip().rstrip(';') + ('; ' if decl.strip() else '') + f'{prop}: {value}'
        return doc.set_attr(el, 'style', decl)
    return doc.set_attr(el, 'style', f'{prop}: {value}')


def _blend_until(start: tuple[int, int, int], other: tuple[int, int, int], target: tuple[int, int, int],
                 needed: float) -> tuple[int, int, int] | None:
    """Move `start` towards `target` in 1% steps until it contrasts with `other` by `needed`."""
    for step in range(0, 101):
        t = step / 100
        cand = tuple(round(start[i] + (target[i] - start[i]) * t) for i in range(3))
        if contrast(cand, other) >= needed + 0.05:
            return cand  # type: ignore[return-value]
    return None


@fixer('color-contrast', mode='mixed')
def color_contrast(doc, el, f, language, values):
    data = (f.data or {}).get('color-contrast') or {}
    fg, bg = _rgb(str(data.get('fgColor', ''))), _rgb(str(data.get('bgColor', '')))
    try:
        needed = float(str(data.get('expectedContrastRatio', '')).split(':')[0])
    except ValueError:
        return None
    if fg is None or bg is None or needed <= 0 or data.get('messageKey'):   # background image/gradient/overlap: a person decides
        return None
    measured = f'{data.get("fgColor")} on {data.get("bgColor")} is {data.get("contrastRatio")}:1 (needs {needed}:1)'
    new = nearest_passing(fg, bg, needed)
    if new is not None and values is None:
        hex_new = '#%02x%02x%02x' % new
        return Draft(_set_style_decl(doc, el, 'color', hex_new + ' !important'), _tag_focus(el),
                     'Darken or lighten this text just enough to meet the required contrast ratio.',
                     f'{measured}; {hex_new} gives {contrast(new, bg):.2f}:1. This adds an inline colour on this element only '
                     f'(marked !important so a style-sheet rule cannot override it); consider fixing the shared style '
                     f'instead.', risk='medium')
    # The text colour cannot move far enough in its own direction (for example white text on mid-grey).
    # Two honest options, both visible changes, so the reviewer chooses.
    away = (0, 0, 0) if _lum(bg) <= _lum(fg) else (255, 255, 255)
    new_bg = _blend_until(bg, fg, away, needed)
    flip = (0, 0, 0) if _lum(fg) > _lum(bg) else (255, 255, 255)
    new_fg = _blend_until(fg, bg, flip, needed)
    options = []
    if new_bg is not None:
        options.append(('bg', f'Change the background behind this text to {"#%02x%02x%02x" % new_bg} '
                              f'({contrast(fg, new_bg):.1f}:1)'))
    if new_fg is not None:
        options.append(('fg', f'Change the text colour to {"#%02x%02x%02x" % new_fg} ({contrast(new_fg, bg):.1f}:1)'))
    if not options:
        return None
    fld = {'name': 'choice', 'label': 'The text colour cannot be adjusted on its own. Which change do you want?',
           'kind': 'select', 'required': True, 'options': options}
    if values is None:
        return Draft(focus=_tag_focus(el), explanation='Low contrast that needs a visible design choice.', evidence=measured,
                     mode='input', fields=(fld,), preview='style="…"', risk='medium')
    choice = str(values.get('choice', ''))
    if choice not in {v for v, _ in options}:
        raise FixInputError('Choose an option from the list.')
    if choice == 'bg':
        hex_bg = '#%02x%02x%02x' % new_bg
        return Draft(_set_style_decl(doc, el, 'background-color', hex_bg + ' !important'), _tag_focus(el),
                     'Change the background behind this text so it meets the contrast ratio.',
                     f'{measured}; reviewer chose background {hex_bg}.', risk='medium')
    hex_fg = '#%02x%02x%02x' % new_fg
    return Draft(_set_style_decl(doc, el, 'color', hex_fg + ' !important'), _tag_focus(el), 'Change the text colour to meet the contrast ratio.',
                 f'{measured}; reviewer chose text colour {hex_fg}.', risk='medium')

# Register the second set of fix templates (import at the end: it uses the helpers above).
from . import fixers_extra  # noqa: E402,F401
