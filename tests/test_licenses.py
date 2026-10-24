from pathlib import Path

from accessloop import licenses

ROOT = Path(__file__).resolve().parent.parent


def test_classify():
    assert licenses.classify('MIT') == 'permissive'
    assert licenses.classify('Apache-2.0 OR BSD-3-Clause') == 'permissive'
    assert licenses.classify('MIT AND PSF-2.0') == 'permissive'
    assert licenses.classify('MPL-2.0') == 'weak-copyleft'
    assert licenses.classify('GNU Lesser General Public License v3 (LGPLv3)') == 'weak-copyleft'
    assert licenses.classify('GPL-3.0-or-later') == 'blocked'
    assert licenses.classify('AGPL-3.0') == 'blocked'
    assert licenses.classify('GNU General Public License v2 (GPLv2)') == 'blocked'
    assert licenses.classify('') == 'unknown'


def test_project_licence_files():
    text = (ROOT / 'LICENSE').read_text(encoding='utf-8')
    assert 'Apache License' in text and 'Version 2.0, January 2004' in text and 'END OF TERMS AND CONDITIONS' in text
    assert 'axe-core' in (ROOT / 'NOTICE').read_text(encoding='utf-8')
    assert (ROOT / 'THIRD_PARTY_NOTICES.md').exists()


def test_no_blocking_licence_in_dependencies():
    rows = licenses.collect()
    assert any(r['name'] == 'axe-core' and r['class'] == 'weak-copyleft' for r in rows)
    assert not [r for r in rows if r['class'] == 'blocked']
    assert '| axe-core |' in licenses.to_markdown(rows)


def test_setup_and_container_files():
    for name in ('setup_mac.sh', 'setup_linux.sh', 'setup_windows.ps1', 'setup_windows.cmd', 'start.sh',
                 'start_windows.cmd', 'Dockerfile', 'docker-compose.yml', '.dockerignore'):
        assert (ROOT / name).exists(), name
    docker = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
    assert 'USER accessloop' in docker and 'npm ci' in docker and 'requirements.lock' in docker
    compose = (ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    assert '127.0.0.1:8501:8501' in compose               # not exposed to the network by default
    assert 'GEMINI_API_KEY: ${GEMINI_API_KEY' in compose   # key comes from the shell, never written in the file
