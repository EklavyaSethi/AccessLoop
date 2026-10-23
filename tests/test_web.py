"""Web layer: API flow, request guards, security headers and report endpoints (real scan; skips without axe)."""
import http.client
import json
import threading

import pytest
from accessloop import scanner
from accessloop.web.server import make_server

pytestmark = pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')


@pytest.fixture(scope='module')
def server():
    srv = make_server(0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def call(server, method, path, body=None, headers=None, host=None, raw=None):
    port = server.server_address[1]
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=60)
    hdrs = {'Host': host or f'127.0.0.1:{port}'}
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        hdrs['Content-Type'] = 'application/json'
    hdrs.update(headers or {})
    conn.request(method, path, body=data, headers=hdrs)
    resp = conn.getresponse()
    payload = resp.read()
    out = (resp.status, dict(resp.getheaders()), payload)
    conn.close()
    return out


def post(server, path, body, **kw):
    status, headers, payload = call(server, 'POST', path, body, **kw)
    return status, headers, json.loads(payload)


def test_static_and_security_headers(server):
    status, headers, body = call(server, 'GET', '/')
    assert status == 200 and b'AccessLoop' in body
    csp = headers['Content-Security-Policy']
    assert "default-src 'self'" in csp
    assert 'unsafe-inline' not in csp
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert 'no-store' in headers['Cache-Control']
    assert call(server, 'GET', '/healthz')[0] == 200


def test_static_path_traversal_and_unknown_routes(server):
    assert call(server, 'GET', '/static/../server.py')[0] == 404
    assert call(server, 'GET', '/static/..%2Fserver.py')[0] == 404
    assert call(server, 'GET', '/nope')[0] == 404
    assert post(server, '/api/nope', {})[0] == 404


def test_host_header_must_be_local(server):
    assert call(server, 'GET', '/api/state', host='evil.example.com')[0] == 403
    assert call(server, 'POST', '/api/reset', {}, host='evil.example.com')[0] == 403


def test_post_guards(server):
    status, _, body = post(server, '/api/reset', {}, headers={'Origin': 'http://evil.example.com'})
    assert status == 403
    status, _, _ = call(server, 'POST', '/api/reset', raw=b'{}', headers={'Content-Type': 'text/plain'})
    assert status == 415
    status, _, _ = call(server, 'POST', '/api/reset', raw=b'{bad', headers={'Content-Type': 'application/json'})
    assert status == 400
    status, _, _ = call(server, 'POST', '/api/reset', raw=b'[]', headers={'Content-Type': 'application/json'})
    assert status == 400


def test_actions_need_a_loaded_and_scanned_page(server):
    post(server, '/api/reset', {})
    status, _, body = post(server, '/api/scan', {'language': 'en'})
    assert status == 409 and 'error' in body
    status, _, body = post(server, '/api/approve', {'id': 'x', 'language': 'en'})
    assert status == 409


def test_unknown_sample_and_unsafe_sample_are_refused(server):
    status, _, _ = post(server, '/api/load', {'sample': '../../etc/passwd'})
    assert status == 400
    status, _, _ = post(server, '/api/load', {'html': '<html><body><script>alert(1)</script></body></html>', 'name': 'x.html'})
    assert status == 400
    status, _, _ = post(server, '/api/load', {'html': 'x' * 300_000, 'name': 'big.html'})
    assert status == 400


def test_full_flow_reject_approve_reports(server):
    status, _, state = post(server, '/api/load', {'sample': 'examples/samples/02_sip_signup.html'})
    assert status == 200 and state['loaded']
    status, _, state = post(server, '/api/scan', {'language': 'en-IN'})
    assert status == 200 and state['proposals']
    pid = state['proposals'][0]['id']

    # stale / unknown proposal ids are refused and nothing is written
    status, _, _ = post(server, '/api/approve', {'id': 'does-not-exist', 'language': 'en-IN', 'reviewer': 'Tester'})
    assert status == 409

    status, _, state = post(server, '/api/reject', {'id': pid, 'reviewer': 'Tester'})
    assert status == 200 and state['metrics']['rejected'] == 1
    assert state['metrics']['current'] == state['metrics']['baseline']

    pid = state['proposals'][0]['id']
    status, _, state = post(server, '/api/approve', {'id': pid, 'language': 'en-IN', 'reviewer': 'Tester'})
    assert status == 200
    assert state['outcome']['status'] == 'verified'
    assert state['metrics']['current'] < state['metrics']['baseline']

    # report endpoints
    status, headers, body = call(server, 'GET', '/api/report.html')
    assert status == 200 and b'evidence report' in body
    assert "default-src 'none'" in headers['Content-Security-Policy']
    assert b'<script' not in body
    status, _, body = call(server, 'GET', '/api/report.json')
    data = json.loads(body)
    assert status == 200 and data['fixes_and_decisions'][-1]['status'] == 'verified'
    for path in ('/api/working.html', '/api/original.html', '/preview/working.html', '/preview/original.html'):
        status, headers, _ = call(server, 'GET', path)
        assert status == 200 and 'sandbox' in headers['Content-Security-Policy']
    status, headers, body = call(server, 'GET', '/api/catalog.csv')
    assert status == 200 and b'rule' in body[:300]

    # reset restores the original
    status, _, state = post(server, '/api/reset', {})
    assert status == 200 and state['changed'] is False


def test_ai_review_falls_back_without_key(server, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    post(server, '/api/load', {'sample': 'examples/samples/02_sip_signup.html'})
    post(server, '/api/scan', {'language': 'en'})
    status, _, body = post(server, '/api/ai-review', {})
    assert status == 200 and 'state' in body


def test_typed_text_flow_and_audit_log(server):
    post(server, '/api/load', {'sample': 'examples/samples/02_sip_signup.html'})
    _, _, state = post(server, '/api/scan', {'language': 'en'})
    alt = next(p for p in state['proposals'] if p['rule'] == 'image-alt')
    assert alt['needs_input'] and alt['fields'] and alt['line']
    # nothing typed -> refused, nothing written
    status, _, _ = post(server, '/api/approve', {'id': alt['id'], 'language': 'en', 'reviewer': 'Tester'})
    assert status == 400
    # markup in typed text is refused
    status, _, _ = post(server, '/api/approve', {'id': alt['id'], 'language': 'en', 'reviewer': 'Tester',
                                                  'values': {'alt': '"><script>x</script>'}})
    assert status == 400
    status, _, state = post(server, '/api/approve', {'id': alt['id'], 'language': 'en', 'reviewer': 'Tester',
                                                      'values': {'alt': 'SIP growth chart'}})
    assert status == 200 and state['outcome']['status'] == 'verified'
    assert 'SIP growth chart' in state['fix_log'][-1]['after']


def test_manual_checks_exports_and_preview(server):
    post(server, '/api/load', {'sample': 'examples/samples/02_sip_signup.html'})
    _, _, state = post(server, '/api/scan', {'language': 'en', 'best_practice': True})
    alt = next(p for p in state['proposals'] if p['rule'] == 'image-alt')
    status, _, body = post(server, '/api/preview', {'id': alt['id'], 'language': 'en', 'values': {'alt': 'SIP chart'}})
    assert status == 200 and body['preview']['would_pass'] and 'SIP chart' in body['preview']['announce_after']
    assert post(server, '/api/manual', {'criterion': '2.4.7', 'result': 'fail', 'notes': 'no focus ring', 'reviewer': 'Tester'})[0] == 200
    assert post(server, '/api/manual', {'criterion': '9.9.9', 'result': 'pass'})[0] == 400
    # a name is mandatory for every decision: no name, a one-letter name or digits only are refused, nothing is written
    for bad in (None, '', ' ', 'T', '1234'):
        status, _, body = post(server, '/api/approve', {'id': alt['id'], 'language': 'en', 'reviewer': bad, 'values': {'alt': 'x'}})
        assert status == 400 and 'name' in str(body).lower()
    assert post(server, '/api/agent', {'risks': ['low']})[0] == 400
    status, _, body = call(server, 'GET', '/api/export/acr')
    assert status == 200 and b'2.4.7' in body and b'Does Not Support' in body
    post(server, '/api/approve', {'id': alt['id'], 'language': 'en', 'reviewer': 'Tester', 'values': {'alt': 'SIP chart'}})
    status, _, body = call(server, 'GET', '/api/export/patch')
    assert status == 200 and b'alt="SIP chart"' in body and body.startswith(b'From ')
    for kind in ('jira', 'github', 'junit'):
        status, _, body = call(server, 'GET', f'/api/export/{kind}')
        assert status == 200 and body
