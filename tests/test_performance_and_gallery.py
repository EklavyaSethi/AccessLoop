import tempfile, time
from pathlib import Path
from accessloop.planner import plan
from accessloop.workflow import Workflow

ROOT = Path(__file__).resolve().parent.parent


def test_planning_is_linear_on_large_pages():
    rows = ''.join(f'<label>Field {i}</label><input name="f{i}" type="text">' for i in range(450))
    src = f'<!doctype html><html lang="en"><head><title>t</title></head><body><main><form>{rows}</form></main></body></html>'
    e = Workflow(Path(tempfile.mkdtemp()))
    e.load(src)
    e.scan()
    t = time.time()
    plan(e.current_html, e.current_scan.findings)
    assert time.time() - t < 2.0 and len(e.proposals) == 450


def test_gallery_all_findings_fixed_and_verified():
    from accessloop.sample_suite import CASES, run_case
    name, file, purpose, body = next(c for c in CASES if c[0].startswith('B8'))
    assert run_case(name, file, purpose, body, None).passed
