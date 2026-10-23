"""AccessLoop checks its own interfaces with the same engine it uses on customers' pages.

    python -m accessloop.selfcheck            # web UI (always) + Streamlit app (when Streamlit is installed)

Unlike customer pages, our own UI is trusted, so it runs with JavaScript on (it is a JavaScript app). Each screen is
checked in several states: empty, page loaded, scanned with proposals, and after a fix. Exit code 1 if any serious or
critical WCAG A/AA violation is found.
"""
from __future__ import annotations
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

from .scanner import AXE_PATH, BEST_PRACTICE_TAGS

ROOT = Path(__file__).resolve().parent.parent
STREAMLIT_PAGES = ['', 'load', 'scan', 'agent', 'review', 'verify', 'manual', 'checklist', 'preview', 'site', 'reports', 'audit',
                   'trace', 'coverage', 'how']


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _axe(page) -> list[dict]:
    page.evaluate(AXE_PATH.read_text(encoding='utf-8') + '\n;0')
    res = page.evaluate("async (tags) => (await axe.run(document, {runOnly: {type: 'tag', values: tags}})).violations",
                        BEST_PRACTICE_TAGS)
    return [{'rule': v['id'], 'impact': v.get('impact'), 'help': v['help'], 'nodes': [n['target'][0] for n in v['nodes']][:5],
             'wcag': [t for t in v['tags'] if t.startswith('wcag')]} for v in res]


def _post(base: str, path: str, body: dict) -> dict:
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json',
                                 'Origin': base})
    with urllib.request.urlopen(req, timeout=120) as r:   # noqa: S310 - our own local server
        return json.loads(r.read())


def _web_ui() -> list[dict]:
    from .web.server import make_server
    srv = make_server(0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{port}'
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            states = [('empty', None), ('loaded', lambda: _post(base, '/api/load', {'sample': 'examples/samples/02_sip_signup.html'})),
                      ('scanned', lambda: _post(base, '/api/scan', {'language': 'en', 'best_practice': True})),
                      ('after a fix', lambda: _post(base, '/api/approve', {'id': _post(base, '/api/scan', {'language': 'en'})['proposals'][0]['id'],
                                                                           'language': 'en', 'reviewer': 'Self check'}))]
            for name, action in states:
                if action:
                    action()
                page.goto(base + '/', wait_until='networkidle')
                for tab in ('workspace', 'preview', 'audit', 'coverage', 'reports'):
                    btn = page.locator(f'#tab-{tab}')
                    if btn.count():
                        btn.click()
                        page.wait_for_timeout(150)
                    for v in _axe(page):
                        results.append({'ui': 'web', 'screen': f'{tab} ({name})', **v})
            browser.close()
    finally:
        srv.shutdown()
        srv.server_close()
    return _dedupe(results)


def _streamlit() -> list[dict]:
    try:
        import streamlit  # noqa: F401
    except ImportError:
        return [{'ui': 'streamlit', 'screen': '-', 'rule': 'skipped', 'impact': None, 'help': 'Streamlit is not installed here',
                 'nodes': [], 'wcag': []}]
    port = _free_port()
    env = {**os.environ, 'ACCESSLOOP_HOME': os.environ.get('ACCESSLOOP_HOME', str(ROOT / '.selfcheck_home'))}
    proc = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app.py'), '--server.headless', 'true',
                             '--server.port', str(port), '--browser.gatherUsageStats', 'false'], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = []
    try:
        base = f'http://127.0.0.1:{port}'
        for _ in range(60):
            try:
                urllib.request.urlopen(base + '/_stcore/health', timeout=1)   # noqa: S310
                break
            except OSError:
                time.sleep(0.5)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            for path in STREAMLIT_PAGES:
                page.goto(f'{base}/{path}', wait_until='networkidle')
                page.wait_for_timeout(1500)
                for v in _axe(page):
                    results.append({'ui': 'streamlit', 'screen': path or 'home', **v})
            browser.close()
    finally:
        proc.terminate()
    return _dedupe(results)


def _in_own_thread(fn) -> list[dict]:
    # Playwright's sync API refuses to start in a thread that already runs one (the scanner keeps a browser per thread).
    box: dict = {}

    def run():
        try:
            box['rows'] = fn()
        except BaseException as error:  # noqa: BLE001 - re-raised in the caller
            box['error'] = error
    th = threading.Thread(target=run, daemon=True)
    th.start()
    th.join()
    if 'error' in box:
        raise box['error']
    return box['rows']


def check_web_ui() -> list[dict]:
    return _in_own_thread(_web_ui)


def check_streamlit() -> list[dict]:
    return _in_own_thread(_streamlit)


def _dedupe(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        key = (r['ui'], r['screen'], r['rule'])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def main() -> int:
    rows = check_web_ui() + check_streamlit()
    serious = [r for r in rows if r['impact'] in ('serious', 'critical')]
    for r in rows:
        print(f'{r["ui"]:<9} {r["screen"]:<24} {str(r["impact"]):<9} {r["rule"]:<28} {r["help"]} {r["nodes"][:2]}')
    print(f'\n{len(rows)} finding(s); {len(serious)} serious or critical.' if rows else 'No accessibility violations found.')
    return 1 if serious else 0


if __name__ == '__main__':
    raise SystemExit(main())
