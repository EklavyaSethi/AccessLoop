"""Real Chromium + axe acceptance over examples/samples. Skips if axe-core isn't installed."""
import pytest
from accessloop import scanner
from accessloop.sample_suite import CASES, run_case

pytestmark = pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')


@pytest.mark.parametrize('name,file,purpose,body', CASES, ids=[c[0] for c in CASES])
def test_sample(name, file, purpose, body):
    result = run_case(name, file, purpose, body, out_dir=None)
    failed = [label for label, ok in result.checks if not ok]
    assert result.passed, failed
