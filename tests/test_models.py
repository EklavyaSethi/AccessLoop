from accessloop.models import ScanResult, Finding
from accessloop.verification import verify


def test_axe_parsing_counts_nodes():
    raw = {'violations': [{'id': 'label', 'impact': 'critical', 'help': 'Missing labels', 'nodes': [
        {'target': ['#a'], 'failureSummary': 'X'}, {'target': ['#b'], 'failureSummary': 'Y'}]}],
        'passes':[{'id':'x'}], 'incomplete':[{'id':'y'}]}
    result = ScanResult.from_axe(raw)
    assert result.counts()['label'] == 2
    assert result.passed_rules == 1 and result.incomplete == 1


def test_verifier_rejects_regression():
    original = ScanResult((Finding('label','#a','serious','A','a'), Finding('html-has-lang','html','serious','B','b')))
    regressed = ScanResult((Finding('label','#a','serious','A','a'), Finding('color-contrast','#b','serious','C','c')))
    ok, msg = verify(original, regressed, 'html-has-lang')
    assert not ok and 'regression' in msg.lower()


def test_verifier_requires_target_improvement():
    original = ScanResult((Finding('label','#a','serious','A','a'),))
    ok, _ = verify(original, original, 'label')
    assert not ok
