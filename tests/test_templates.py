from accessloop.htmlsource import Edit
from accessloop.templates import map_edits, render_jinja


def test_edits_carry_into_template_only_where_text_matches():
    template = '<html>\n<body>\n<label>Name</label>\n<input id="n" value="{{ name }}">\n<label>Phone</label>\n<input id="p">\n</body></html>'
    rendered = render_jinja(template, {'name': ''})
    pos = rendered.index('<label>Phone') + len('<label')
    mapped, failed = map_edits(rendered, template, [Edit(pos, pos, ' for="p"')])
    assert not failed
    from accessloop.htmlsource import apply_edits
    assert '<label for="p">Phone</label>' in apply_edits(template, mapped)
    # an element inside a loop is fixed once in the loop body, which fixes every rendered copy
    t2 = '<ul>{% for x in xs %}<li><img src="{{ x }}.png"></li>{% endfor %}</ul>'
    r2 = render_jinja(t2, {'xs': ['a', 'b']})
    pos2 = r2.index('<img') + 4
    m2, f2 = map_edits(r2, t2, [Edit(pos2, pos2, ' alt=""')])
    assert not f2 and render_jinja(apply_edits(t2, m2), {'xs': ['a', 'b']}).count('alt=""') == 2
    # markup injected by an expression does not exist in the template: reported, never guessed
    t3 = '<div>{{ banner|safe }}</div>'
    r3 = render_jinja(t3, {'banner': '<img src="promo.png">'})
    pos3 = r3.index('<img') + 4
    m3, f3 = map_edits(r3, t3, [Edit(pos3, pos3, ' alt=""')])
    assert not m3 and f3
