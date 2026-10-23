"""Real-browser end-to-end smoke check. Run after pip, npm, and Chromium installation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from .workflow import Workflow


def main() -> None:
    source = (Path(__file__).resolve().parent.parent / 'examples/student_registration.html').read_text(encoding='utf-8')
    with TemporaryDirectory() as tmp:
        workflow = Workflow(Path(tmp))
        workflow.load(source)
        baseline = workflow.scan()
        print('Initial detected counts:', dict(baseline.counts()))
        expected = {'html-has-lang', 'label', 'button-name'}
        if not expected.issubset(baseline.counts().keys()):
            raise AssertionError(f'Expected 3 seeded axe rules, got {dict(baseline.counts())}')
        attempts = 0
        while workflow.proposals:
            p = workflow.proposals[0]
            result = workflow.apply(p.proposal_id, approved=True)
            print(p.rule_id, result.status, result.detail)
            if result.status != 'verified':
                raise AssertionError('Smoke test failed: ' + result.detail)
            attempts += 1
            if attempts > 3:
                raise AssertionError('Unexpected additional proposals')
        remaining = workflow.current_scan.counts()
        if any(remaining[rule] for rule in expected):
            raise AssertionError(f'Seeded findings remain: {remaining}')
        print('PASS: three seeded findings fixed, independently rescanned, report available.')


if __name__ == '__main__':
    main()
