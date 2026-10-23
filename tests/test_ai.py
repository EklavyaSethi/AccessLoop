import pytest
from accessloop import ai_advisor as ai
from accessloop.models import Proposal


def _p():
    return Proposal('id1', 'label', '#acct', 'x', 'Account 123456789012 for a@b.co', '<input id="acct" value="123456789012" placeholder="PAN ABCDE1234F">',
                    'aria-label="Account"', 'sha', 'new', finding_index=0)


def test_off_by_default_and_needs_consent(monkeypatch):
    monkeypatch.delenv('ACCESSLOOP_AI', raising=False)
    with pytest.raises(ai.AIUnavailable):
        ai.review_proposals((_p(),), consent=True)
    monkeypatch.setenv('ACCESSLOOP_AI', 'gemini')
    with pytest.raises(ai.AIUnavailable):
        ai.review_proposals((_p(),), consent=False)


def test_redaction_removes_values_numbers_and_emails():
    sent = ai.payload_for((_p(),))[0]
    blob = str(sent)
    assert '123456789012' not in blob and 'ABCDE1234F' not in blob and 'a@b.co' not in blob
    assert '[redacted]' in sent['before']


def test_local_model_must_be_on_this_machine(monkeypatch):
    monkeypatch.setenv('ACCESSLOOP_AI', 'local')
    monkeypatch.setenv('OLLAMA_URL', 'http://evil.example:11434')
    with pytest.raises(ai.AIUnavailable):
        ai.review_proposals((_p(),), consent=True)
