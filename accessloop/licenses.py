"""Licence check for everything AccessLoop ships with or downloads.

    python -m accessloop.licenses            # table of every pinned dependency and its licence; exit 1 on a blocker
    python -m accessloop.licenses --md       # the same as Markdown (for docs/LICENSES_REPORT.md)

AccessLoop itself is Apache-2.0. A dependency under a strong copyleft licence (GPL, AGPL, SSPL) would change what a bank
may do with the code, so CI fails if one appears. Weak copyleft (MPL-2.0, LGPL) is allowed when the library is used
unmodified, which is how AccessLoop uses axe-core (MPL-2.0) and certifi (MPL-2.0); anything unrecognised is listed for a
person to check. Licences are read from the installed packages' own metadata and from package-lock.json.
"""
from __future__ import annotations
import json
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BLOCK = re.compile(r'\b(A?GPL|GNU General Public|Affero|SSPL|Server Side Public|Commons Clause|BUSL|Business Source)', re.I)
WEAK = re.compile(r'\b(LGPL|Lesser General|MPL|Mozilla Public|EPL|Eclipse Public)', re.I)
PERMISSIVE = re.compile(r'\b(MIT|BSD|Apache|ISC|PSF|Python Software Foundation|HPND|Unlicense|Zlib|CC0|0BSD|MIT-CMU)', re.I)


def classify(licence: str) -> str:
    """'blocked', 'weak-copyleft', 'permissive' or 'unknown'. Dual licences ('Apache-2.0 OR BSD') take the best option."""
    text = licence or ''
    options = re.split(r'\s+OR\s+|\s+or\s+|/', text) if ' OR ' in text or ' or ' in text else [text]
    best = 'unknown'
    for opt in options:
        if PERMISSIVE.search(opt) and not BLOCK.search(opt) and not WEAK.search(opt):
            return 'permissive'
        if WEAK.search(opt) and not re.search(r'\bGPL', opt.replace('LGPL', '')):
            best = 'weak-copyleft'
        elif BLOCK.search(opt) and best == 'unknown':
            best = 'blocked'
    return best


def _licence_of(dist) -> str:
    md = dist.metadata
    lic = (md.get('License-Expression') or '').strip()
    if lic:
        return lic
    classifiers = [c.split('::')[-1].strip() for c in md.get_all('Classifier') or [] if c.startswith('License ::')]
    classifiers = [c for c in classifiers if c not in ('OSI Approved',)]
    if classifiers:
        return ' OR '.join(classifiers)
    lic = (md.get('License') or '').strip()
    return lic.splitlines()[0][:80] if lic else ''


def pinned_python() -> list[str]:
    names = []
    for f in ('requirements.lock', 'requirements-ai.txt'):
        p = ROOT / f
        if p.exists():
            for line in p.read_text(encoding='utf-8').splitlines():
                m = re.match(r'\s*([A-Za-z0-9_.\-]+)\s*(==|>=|<|$)', line)
                if m and not line.strip().startswith(('#', '-r')):
                    names.append(m.group(1))
    return names


def collect() -> list[dict]:
    rows = []
    for name in pinned_python():
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue                                     # optional (AI) packages that are not installed
        lic = _licence_of(dist)
        rows.append({'name': dist.metadata['Name'], 'version': dist.version, 'source': 'PyPI', 'licence': lic or '(not stated)',
                     'class': classify(lic)})
    lock = ROOT / 'package-lock.json'
    if lock.exists():
        for path, info in (json.loads(lock.read_text(encoding='utf-8')).get('packages') or {}).items():
            if path.startswith('node_modules/'):
                lic = info.get('license', '')
                rows.append({'name': path.split('node_modules/')[-1], 'version': info.get('version', ''), 'source': 'npm',
                             'licence': lic or '(not stated)', 'class': classify(lic)})
    rows.append({'name': 'Chromium (downloaded by Playwright)', 'version': 'as pinned by Playwright', 'source': 'Playwright CDN',
                 'licence': 'BSD-3-Clause and others', 'class': 'permissive'})
    return sorted(rows, key=lambda r: (r['class'] != 'blocked', r['class'] != 'unknown', r['name'].lower()))


NOTE = {'permissive': 'ok', 'weak-copyleft': 'ok if used unmodified', 'unknown': 'check by hand', 'blocked': 'BLOCKER'}


def to_markdown(rows: list[dict]) -> str:
    lines = ['| Package | Version | From | Licence | Status |', '|---|---|---|---|---|']
    lines += [f"| {r['name']} | {r['version']} | {r['source']} | {r['licence']} | {NOTE[r['class']]} |" for r in rows]
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    rows = collect()
    if '--md' in argv:
        print(to_markdown(rows))
    else:
        for r in rows:
            print(f"{NOTE[r['class']]:<22} {r['name']:<36} {r['version']:<14} {r['licence']}")
    blocked = [r for r in rows if r['class'] == 'blocked']
    unknown = [r for r in rows if r['class'] == 'unknown']
    print(f"\n{len(rows)} components: {len(blocked)} blocker(s), {len(unknown)} to check by hand. AccessLoop is Apache-2.0.",
          file=sys.stderr)
    return 1 if blocked else 0


if __name__ == '__main__':
    raise SystemExit(main())
