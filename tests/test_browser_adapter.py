"""Adapter-only Chromium test; the stub is NOT an axe-core integration result."""
import shutil
import pytest
from accessloop import scanner


def test_browser_js_injection_and_result_parsing(tmp_path, monkeypatch):
    executable = shutil.which('chromium') or shutil.which('chromium-browser')
    if not executable:
        pytest.skip('System Chromium absent. Real axe smoke test runs separately after setup.')
    stub = tmp_path/'axe_stub.js'
    stub.write_text('''window.axe = { run: async function(doc, options) {
      return { violations: [ { id: 'html-has-lang', impact: 'serious', help: 'Missing lang',
      nodes: [{ target: ['html'], failureSummary: 'Missing language' }] } ],
      passes: [], incomplete: [] };
    }};''')
    monkeypatch.setattr(scanner, 'AXE_PATH', stub)
    monkeypatch.setenv('ACCESSLOOP_CHROMIUM_EXECUTABLE', executable)
    result = scanner.scan_html('<html><body><h1>Hello</h1></body></html>')
    assert len(result.findings) == 1
    assert result.findings[0].selector == 'html'
    assert result.findings[0].rule_id == 'html-has-lang'
