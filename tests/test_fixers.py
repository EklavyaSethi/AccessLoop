import pytest
from accessloop.fixers import contrast, nearest_passing, FIXERS, clean_text, FixInputError


def test_contrast_ratio_known_values():
    assert round(contrast((0, 0, 0), (255, 255, 255)), 1) == 21.0
    assert round(contrast((119, 119, 119), (255, 255, 255)), 1) == 4.5


def test_nearest_passing_colour_meets_aa():
    for fg, bg in [((170, 170, 170), (255, 255, 255)), ((90, 90, 90), (30, 30, 30)), ((200, 120, 120), (255, 240, 240))]:
        assert contrast(nearest_passing(fg, bg, 4.5), bg) >= 4.5


def test_every_registered_fixer_has_a_valid_mode():
    assert FIXERS and all(callable(f) for f in FIXERS.values())


def test_clean_text_rejects_markup_and_empty():
    for bad in ('', '   ', '<script>x</script>', 'a"b\n<c'):
        with pytest.raises(FixInputError):
            clean_text(bad)
    assert clean_text('  Pay  now ') == 'Pay now'
