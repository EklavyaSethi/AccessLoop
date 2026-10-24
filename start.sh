#!/usr/bin/env bash
# Start AccessLoop (macOS / Linux) after setup_mac.sh or setup_linux.sh. Opens http://localhost:8501
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || { echo "Run the setup script first (setup_mac.sh or setup_linux.sh)."; exit 1; }
# shellcheck disable=SC1091
source .venv/bin/activate
exec python -m streamlit run app.py "$@"
