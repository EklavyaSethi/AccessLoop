from accessloop.models import Finding
from accessloop.planner import plan


def test_only_expected_templates_generated(source):
    findings = (
        Finding('html-has-lang','html','serious','lang',''),
        Finding('label','#email','serious','label',''),
        Finding('button-name','#submit-registration','serious','button',''),
        Finding('image-alt','#photo','serious','alt',''),
    )
    proposals = plan(source, findings)
    assert len(proposals) == 3
    html = next(p.new_html for p in proposals if p.rule_id == 'html-has-lang')
    assert '<html lang="en">' in html
    label = next(p for p in proposals if p.rule_id == 'label')
    assert '<label for="email">University email</label>' in label.new_html
    button = next(p for p in proposals if p.rule_id == 'button-name')
    assert '<span>Submit registration</span>' in button.new_html
    assert 'aria-hidden="true"' not in button.new_html


def test_different_selector_does_not_patch_other_input(source):
    finding = Finding('label','#not-the-input','critical','label','')
    assert not plan(source, (finding,))


def test_no_unsupported_language(source):
    finding = Finding('html-has-lang','html','serious','lang','')
    assert not plan(source, (finding,), language='not valid')


def test_data_lang_does_not_block_real_lang_patch(source):
    finding = Finding('html-has-lang', 'html', 'serious', 'lang', '')
    modified = source.replace('<html>', '<html data-lang="candidate">')
    proposals = plan(modified, (finding,))
    assert len(proposals) == 1
    assert '<html data-lang="candidate" lang="en">' in proposals[0].new_html


def test_id_prefix_collision_cannot_select_wrong_control(source):
    finding = Finding('label', '#email2', 'serious', 'label', '')
    assert plan(source, (finding,)) == ()
