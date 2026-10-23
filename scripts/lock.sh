#!/bin/sh
# Rebuild requirements.lock with exact versions AND sha256 hashes (needs internet), then audit for known vulnerabilities.
set -e
python -m pip install --upgrade pip-tools pip-audit
pip-compile --generate-hashes --allow-unsafe --output-file requirements.lock requirements.txt
python -m pip install --require-hashes -r requirements.lock
pip-audit -r requirements.lock
npm ci --no-audit --no-fund && npm audit --omit=dev
python -m accessloop.sbom > sbom.cdx.json
echo "requirements.lock (with hashes) and sbom.cdx.json updated."
