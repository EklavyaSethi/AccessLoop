#!/usr/bin/env bash
# AccessLoop setup for Linux (Ubuntu/Debian, Fedora, Arch ...). Tested in CI on Ubuntu.
#
#   bash setup_linux.sh            # venv, pinned packages, Chromium, axe-core, tests, smoke test
#   bash setup_linux.sh --deps     # also install Chromium's system libraries (uses sudo; Debian/Ubuntu only)
#   bash setup_linux.sh --ai       # also install the optional AI drafting packages (Gemini / local model)
#   bash setup_linux.sh --quick    # skip the tests (not recommended the first time)
set -euo pipefail
cd "$(dirname "$0")"

DEPS=0; AI=0; QUICK=0
for arg in "$@"; do
  case "$arg" in
    --deps) DEPS=1 ;;
    --ai) AI=1 ;;
    --quick) QUICK=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg (try --help)"; exit 2 ;;
  esac
done

say() { printf '\n==> %s\n' "$*"; }
PY=${PYTHON:-python3}

command -v "$PY" >/dev/null || { echo "Python 3.11+ is required (sudo apt install python3 python3-venv)."; exit 1; }
"$PY" - <<'EOF' || { echo "Python 3.11 or newer is required."; exit 1; }
import sys
sys.exit(0 if sys.version_info >= (3, 11) else 1)
EOF
command -v npm >/dev/null || { echo "Node.js with npm is required (https://nodejs.org, or: sudo apt install nodejs npm)."; exit 1; }

say "Creating the virtual environment (.venv)"
if ! "$PY" -m venv .venv; then
  echo "Could not create a virtual environment. On Debian/Ubuntu: sudo apt install python3-venv"; exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip -q

say "Installing the exact package versions AccessLoop is tested with (requirements.lock)"
python -m pip install -r requirements.lock
if [ "$AI" = 1 ]; then
  say "Installing the optional AI drafting packages"
  python -m pip install -r requirements-ai.txt
fi

if [ "$DEPS" = 1 ]; then
  say "Installing Chromium and its system libraries (sudo)"
  if [ "$(id -u)" = 0 ]; then python -m playwright install-deps chromium
  else sudo "$(command -v python)" -m playwright install-deps chromium; fi
  python -m playwright install chromium          # the browser itself goes into this user's cache, not root's
else
  say "Installing Chromium (the sandboxed scanner browser)"
  python -m playwright install chromium
fi

say "Installing axe-core locally (no CDN is used during scans)"
if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi

if [ "$QUICK" = 0 ]; then
  say "Running the tests"
  python -m pytest -q
  say "Real-browser smoke test (scan, approve, patch, re-scan)"
  if ! python -m accessloop.smoke; then
    echo
    echo "The browser could not start. Chromium needs some system libraries; install them with:"
    echo "    bash setup_linux.sh --deps"
    exit 1
  fi
fi

printf '\nSetup complete. Start AccessLoop with:\n    bash start.sh\n(or: source .venv/bin/activate && streamlit run app.py)\n'
