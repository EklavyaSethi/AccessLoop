"""Property-based fuzzing of the HTML reader and every fix template (seeded, so failures reproduce).

For thousands of random, messy documents and random findings, every fixer must:
  * never raise an exception (a bad page must not crash the agent),
  * produce non-overlapping edits that apply cleanly,
  * leave comments, scripts and styles byte-for-byte untouched,
  * produce a document the reader can parse again.
"""
import random
import re

from accessloop.fixers import FIXERS, FixInputError
from accessloop.htmlsource import Doc, apply_edits
from accessloop.models import Finding
from accessloop.planner import propose_one, sha256

TAGS = ['div', 'span', 'p', 'a', 'button', 'input', 'img', 'label', 'select', 'ul', 'ol', 'li', 'dl', 'dt', 'dd', 'table',
        'tr', 'td', 'th', 'h1', 'h2', 'h4', 'h6', 'form', 'nav', 'header', 'footer', 'section', 'main', 'iframe', 'video',
        'details', 'summary', 'svg', 'meta', 'blink', 'marquee', 'object', 'area', 'textarea']
ATTRS = ['id', 'class', 'role', 'aria-label', 'aria-hidden', 'tabindex', 'href', 'src', 'alt', 'title', 'lang', 'type',
         'aria-expanded', 'style', 'for', 'headers', 'scope', 'accesskey', 'autocomplete', 'aria-checked', 'name', 'value']
VALUES = ['x', '', 'true', 'false', '-1', '3', 'main', 'button', 'list', 'a "quoted" > value', "it's", '#t', 'color: #777',
          'en', 'english', 'text', 'off', 'yes', 'a b c']


def _attr(rng):
    name = rng.choice(ATTRS)
    v = rng.choice(VALUES)
    q = rng.choice(['"', "'", ''])
    if q == '' and re.search(r'[\s"\'>=]', v) or v == '':
        q = '"'
    if q == "'" and "'" in v:
        q = '"'
    if q == '"' and '"' in v:
        v = v.replace('"', '&quot;')
    return f' {name}={q}{v}{q}' if rng.random() > 0.1 else f' {name}'


def _node(rng, depth):
    r = rng.random()
    if depth > 4 or r < 0.25:
        return rng.choice(['text', ' Pay now ', '&amp; more', '<!-- <img src=x> -->', '₹ 2,500', '\n  '])
    if r < 0.32:
        return '<script>if (a < b) { document.write("<p>") }</script>'
    if r < 0.36:
        return '<style>p > a { color: red }</style>'
    tag = rng.choice(TAGS)
    attrs = ''.join(_attr(rng) for _ in range(rng.randint(0, 4)))
    if tag in ('input', 'img', 'meta', 'area') or rng.random() < 0.05:
        return f'<{tag}{attrs}{"/" if rng.random() < 0.3 else ""}>'
    kids = ''.join(_node(rng, depth + 1) for _ in range(rng.randint(0, 3)))
    close = f'</{tag}>' if rng.random() > 0.15 else ''          # implied/unclosed end tags too
    return f'<{tag}{attrs}>{kids}{close}'


def _doc(rng):
    head = '<head><title>t</title><meta name="viewport" content="width=device-width, maximum-scale=1"></head>' \
        if rng.random() < 0.7 else ''
    html_attrs = ''.join(_attr(rng) for _ in range(rng.randint(0, 2)))
    return f'<!doctype html><html{html_attrs}>{head}<body>' + ''.join(_node(rng, 0) for _ in range(rng.randint(1, 6))) + '</body></html>'


def _protected(source, doc):
    out = []
    for e in doc.elements:
        if e.tag in ('script', 'style') and e.end_start is not None:
            out.append(source[e.start_end:e.end_start])
    return out + re.findall(r'<!--.*?-->', source, re.S)


def test_fixers_never_crash_and_never_touch_scripts_or_comments():
    rng = random.Random(20261023)
    rules = sorted(FIXERS)
    checked = 0
    for _ in range(400):
        source = _doc(rng)
        doc = Doc(source)
        if not doc.elements:
            continue
        protected = _protected(source, doc)
        for _ in range(6):
            el = rng.choice(doc.elements)
            rule = rng.choice(rules)
            data = {'color-contrast': {'fgColor': '#777777', 'bgColor': '#ffffff', 'contrastRatio': 4.48,
                                       'expectedContrastRatio': '4.5:1'},
                    'aria-required-attr': ['aria-checked'], 'aria-allowed-attr': {'values': ['aria-checked="true"']},
                    'landmark-is-unique': {'role': 'navigation'}}
            f = Finding(rule, el.tag, 'serious', 'h', 'd', uid=el.uid, data=data)
            for values in (None, {'text': 'Name', 'alt': 'Chart', 'title': 'Page title', 'lang': 'en', 'token': 'email',
                                  'choice': 'show', 'main': 'wrap', 'keep': '0', 'name': 'Region', 'src': 'a.vtt',
                                  'n0': 'One', 'n1': 'Two', 'aria-checked': 'false', 'c0': 'dt'}):
                try:
                    p = propose_one(doc, sha256(source), 0, f, 'en', values)
                except FixInputError:
                    continue                      # refusing bad typed input is correct behaviour
                if p is None or p.needs_input:
                    continue
                new = apply_edits(source, list(p.edits))    # raises on overlapping edits
                assert new == p.new_html
                for block in protected:
                    assert block in new, (rule, block[:40])
                Doc(new)                                     # parses again
                checked += 1
    assert checked > 500


def test_reader_round_trips_random_documents():
    rng = random.Random(7)
    for _ in range(300):
        source = _doc(rng)
        doc = Doc(source)
        for e in doc.elements:
            assert source[e.start] == '<' and e.start < e.start_end <= len(source)
            if e.end_end is not None:
                assert e.start_end <= e.end_start <= e.end_end
