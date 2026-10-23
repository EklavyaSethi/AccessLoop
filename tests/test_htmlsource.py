from accessloop.htmlsource import Doc, apply_edits, Edit, instrument


def test_comments_and_scripts_are_not_elements():
    d = Doc('<html><body><!-- <img src=x> --><p>hi</p><textarea><img></textarea></body></html>')
    tags = [e.tag for e in d.by_uid.values()]
    assert 'img' not in tags and 'p' in tags


def test_quoted_attribute_containing_gt_and_single_quotes():
    d = Doc('<a href=\'x>y\' title="a > b" id=k>t</a>')
    a = next(iter(d.by_uid.values()))
    assert a.value('href') == 'x>y' and a.value('title') == 'a > b' and a.value('id') == 'k'


def test_implied_end_tags_for_li_and_p():
    d = Doc('<ul><li>a<li>b</ul><p>x<p>y')
    li = [e for e in d.by_uid.values() if e.tag == 'li']
    assert len(li) == 2 and li[0].end_end <= li[1].start


def test_set_attr_on_self_closing_and_plain_tags():
    src = '<img src="a.png"/><input type=text>'
    d = Doc(src)
    img, inp = list(d.by_uid.values())
    out = apply_edits(src, [*d.set_attr(img, 'alt', 'x'), *d.set_attr(inp, 'aria-label', 'y')])
    assert out == '<img src="a.png" alt="x"/><input type=text aria-label="y">'


def test_overlapping_edits_are_rejected():
    try:
        apply_edits('abcdef', [Edit(0, 3, 'x'), Edit(2, 4, 'y')])
    except Exception:
        return
    raise AssertionError('overlap not detected')


def test_instrument_adds_uid_to_every_start_tag_only_in_the_copy():
    src = '<div><p>a</p><!-- <b> --></div>'
    out = instrument(Doc(src))
    assert out.count('data-al-uid=') == 2 and 'data-al-uid' not in src


def test_scan_copy_removes_everything_that_could_run():
    from accessloop.htmlsource import scan_copy
    src = ('<html><head><base href="https://evil.example/"><script>steal()</script></head>'
           '<body onload="x()"><a href="javascript:x()">a</a><iframe srcdoc="<script>x()</script>" title="f"></iframe>'
           '<img src="p.png" onerror="x()" alt=""><p>kept</p></body></html>')
    out = scan_copy(Doc(src))
    low = out.lower()
    for bad in ('<script', 'onload=', 'onerror=', 'javascript:', 'srcdoc', 'evil.example'):
        assert bad not in low, bad
    assert "script-src 'none'" in out and '<p data-al-uid=' in out and 'src="p.png"' in out
