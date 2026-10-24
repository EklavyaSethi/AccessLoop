"""'Where is this on the page?': a reviewer can place a one-line fix inside a large file."""
import time
from pathlib import Path

import pytest
from accessloop import context, scanner
from accessloop.htmlsource import Doc

ROOT = Path(__file__).resolve().parent.parent
needs_axe = pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')

PAGE = """<!doctype html><html lang="en"><head><title>Statements</title></head><body>
<header><nav aria-label="Main"><a href="/">Home</a></nav></header>
<main>
<h1>Your accounts</h1>
<h2>Nominee details</h2>
<form aria-label="Update nominee">
<fieldset><legend>Nominee</legend>
<label>Mobile number</label>
<input id="nom-mobile" name="nominee_mobile" type="tel">
</fieldset>
</form>
<img src="/img/fd-rates-chart.png">
</main></body></html>"""


def _uid(tag, **attrs):
    doc = Doc(PAGE)
    return next(e.uid for e in doc.elements if e.tag == tag and all(e.value(k) == v for k, v in attrs.items()))


def test_sentence_breadcrumb_and_lines_for_a_field():
    c = context.describe(PAGE, _uid('input', id='nom-mobile'))
    assert c['found'] and c['visible']
    assert 'tel field' in c['sentence'] and 'Mobile number' in c['sentence'] and 'Nominee details' in c['sentence']
    assert 'form "Update nominee"' in c['sentence'] or 'group "Nominee"' in c['sentence']
    assert c['breadcrumb'][0] == 'page' and any('main content' in b for b in c['breadcrumb'])
    assert any(b.startswith('group "Nominee"') for b in c['breadcrumb'])
    changed = [ln for ln in c['lines'] if ln['changed']]
    assert changed and changed[0]['n'] == c['first_line'] == 9 and 'nom-mobile' in changed[0]['text']
    assert c['lines'][0]['n'] == 3 and c['total_lines'] == PAGE.count('\n') + 1


def test_image_page_settings_and_unknown():
    c = context.describe(PAGE, _uid('img'))
    assert 'image' in c['sentence'] and 'fd-rates-chart.png' in c['sentence']
    c = context.describe(PAGE, _uid('html'))
    assert not c['visible'] and 'page itself' in c['sentence']
    assert context.describe(PAGE, None)['found'] is False


def test_large_file_is_fast_and_shows_only_the_neighbourhood():
    rows = '\n'.join(f'<p id="p{i}">Paragraph {i} about deposits</p>' for i in range(1500))
    big = f'<!doctype html><html lang="en"><body><main><h2>Terms</h2>\n{rows}\n<input id="last" name="pin"></main></body></html>'
    uid = next(e.uid for e in Doc(big).elements if e.value('id') == 'last')
    t0 = time.perf_counter()
    for _ in range(100):                              # a review screen with 100 proposals on one page
        c = context.describe(big, uid)
    assert time.perf_counter() - t0 < 2.0
    assert c['first_line'] > 1500 and len(c['lines']) <= 14 and 'Terms' in c['sentence']


@needs_axe
def test_picture_of_an_element_and_none_for_page_settings():
    png = scanner.element_shot(PAGE, _uid('input', id='nom-mobile'))
    assert png and png[:8] == b'\x89PNG\r\n\x1a\n'
    assert scanner.element_shot(PAGE, _uid('title')) is None


@needs_axe
def test_session_where_and_picture():
    from accessloop.web.server import Session
    s = Session(ROOT)
    s.load(None, '', 'examples/samples/02_sip_signup.html')
    s.scan('en')
    p = s.state()['proposals'][0]
    c = s.where(p['id'])
    assert c['sentence'] and c['lines'] and any(ln['changed'] for ln in c['lines'])
    if c['visible']:
        assert s.picture(p['id'])[:4] == b'\x89PNG'
