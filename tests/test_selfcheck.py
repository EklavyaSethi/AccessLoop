import pytest
from accessloop import scanner


@pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')
def test_our_own_web_ui_has_no_serious_accessibility_violations():
    from accessloop.selfcheck import check_web_ui
    rows = check_web_ui()
    serious = [r for r in rows if r['impact'] in ('serious', 'critical')]
    assert not serious, serious
