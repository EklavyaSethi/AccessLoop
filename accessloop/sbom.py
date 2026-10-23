"""Software bill of materials (CycloneDX 1.5 JSON) for the environment AccessLoop is running in.

    python -m accessloop.sbom > sbom.cdx.json

Lists every installed Python distribution (name, version, licence, package URL) and the npm packages from
package-lock.json with their integrity hashes (axe-core is the one that runs inside the scan).
"""
from __future__ import annotations
import json
import sys
import uuid
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from . import __version__

ROOT = Path(__file__).resolve().parent.parent


def _python_components() -> list[dict]:
    out = []
    for dist in sorted(metadata.distributions(), key=lambda d: (d.metadata['Name'] or '').lower()):
        name, version = dist.metadata['Name'], dist.version
        if not name:
            continue
        comp = {'type': 'library', 'bom-ref': f'pkg:pypi/{name.lower()}@{version}', 'name': name, 'version': version,
                'purl': f'pkg:pypi/{name.lower().replace("_", "-")}@{version}'}
        lic = dist.metadata.get('License-Expression') or dist.metadata.get('License')
        if lic and len(lic) < 100:
            comp['licenses'] = [{'expression': lic}] if dist.metadata.get('License-Expression') else [{'license': {'name': lic}}]
        out.append(comp)
    return out


def _npm_components() -> list[dict]:
    lock = ROOT / 'package-lock.json'
    if not lock.exists():
        return []
    data = json.loads(lock.read_text(encoding='utf-8'))
    out = []
    for path, info in (data.get('packages') or {}).items():
        if not path.startswith('node_modules/'):
            continue
        name = path.split('node_modules/')[-1]
        comp = {'type': 'library', 'bom-ref': f'pkg:npm/{name}@{info.get("version")}', 'name': name,
                'version': info.get('version', ''), 'purl': f'pkg:npm/{name.replace("@", "%40")}@{info.get("version")}'}
        if info.get('license'):
            comp['licenses'] = [{'license': {'id': info['license']}}]
        integrity = info.get('integrity', '')
        if integrity.startswith('sha512-'):
            import base64
            comp['hashes'] = [{'alg': 'SHA-512', 'content': base64.b64decode(integrity[7:]).hex()}]
        out.append(comp)
    return out


def build() -> dict:
    return {
        'bomFormat': 'CycloneDX', 'specVersion': '1.5', 'serialNumber': f'urn:uuid:{uuid.uuid4()}', 'version': 1,
        'metadata': {'timestamp': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                     'component': {'type': 'application', 'name': 'AccessLoop', 'version': __version__,
                                   'bom-ref': f'accessloop@{__version__}'},
                     'properties': [{'name': 'python', 'value': sys.version.split()[0]}]},
        'components': _python_components() + _npm_components(),
    }


if __name__ == '__main__':
    print(json.dumps(build(), indent=1))
