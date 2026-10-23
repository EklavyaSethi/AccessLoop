#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo 'Install Python 3.11+ first.'; exit 1; }
command -v npm >/dev/null || { echo 'Install Node.js LTS first (npm is required).'; exit 1; }
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
npm install --no-audit --no-fund
python -m pytest -q
python -m accessloop.smoke
printf '\nSetup complete. Run: source .venv/bin/activate && streamlit run app.py\n'
