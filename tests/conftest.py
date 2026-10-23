import re
import pytest
from accessloop.models import Finding, ScanResult
from pathlib import Path


@pytest.fixture
def source():
    return (Path(__file__).resolve().parent.parent / 'examples/student_registration.html').read_text(encoding='utf-8')


def fake_scanner(html: str) -> ScanResult:
    findings = []
    if not re.search(r'<html\b[^>]*\blang=', html, re.I):
        findings.append(Finding('html-has-lang', 'html', 'serious', 'HTML must have a language', 'Missing language'))
    if re.search(r'<label>University email</label>\s*<input\b[^>]*id="email"', html, re.I):
        findings.append(Finding('label', '#email', 'critical', 'Form elements must have labels', 'Missing label'))
    if re.search(r'<button\b[^>]*id="submit-registration"[^>]*>\s*<span aria-hidden="true">', html, re.I):
        findings.append(Finding('button-name', '#submit-registration', 'critical', 'Buttons must have discernible text', 'Missing button name'))
    return ScanResult(tuple(findings), 0, 17)


# Accounts are switched on by a users.json in ACCESSLOOP_HOME; tests never touch the real one.
import os as _os
import tempfile as _tempfile
_os.environ.setdefault('ACCESSLOOP_HOME', _tempfile.mkdtemp(prefix='accessloop-test-home-'))
