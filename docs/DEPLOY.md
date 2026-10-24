# Installing and deploying AccessLoop

AccessLoop runs **on the organisation's own machines**. Pages, accounts, signing keys and the audit log never leave
them; the only optional outbound call is AI drafting (Gemini), which is off by default, needs consent per run and
sends redacted text. There are four supported ways to run it, all tested in CI on clean machines
(`.github/workflows/platforms.yml`).

| Where | Command | Tested in CI on |
|---|---|---|
| macOS | `bash setup_mac.sh` then `bash start.sh` | (developed on macOS, Python 3.14) |
| Linux | `bash setup_linux.sh --deps` then `bash start.sh` | Ubuntu (latest GitHub runner), Python 3.12 |
| Windows 10/11 | `setup_windows.cmd` then `start_windows.cmd` | Windows Server (latest GitHub runner), Python 3.12 |
| Any server with Docker | `docker compose up --build` | Ubuntu, image built and smoke-tested |

Every setup script installs the **exact tested versions** (`requirements.lock`, `package-lock.json`), downloads the
sandboxed Chromium, then runs the full test suite and the real-browser smoke test, so a broken install is caught at
install time, not during a demo. The app opens at **http://localhost:8501**.

## Requirements

- **Python 3.11 or newer** and **Node.js LTS (npm)**, not needed for Docker.
- About 1 GB of disk (Chromium plus Python packages), 2 GB of RAM.
- Internet during setup only. Scanning, fixing and verifying work fully offline; axe-core is installed locally and
  scanned pages cannot reach the network.

## macOS

```bash
bash setup_mac.sh
bash start.sh
```

## Linux (Ubuntu/Debian; other distributions work with the libraries installed by hand)

```bash
sudo apt install python3 python3-venv nodejs npm   # if not installed
bash setup_linux.sh --deps     # --deps installs Chromium's system libraries with sudo (once per machine)
bash start.sh
```

Options: `--ai` also installs the AI drafting packages; `--quick` skips the tests.

## Windows 10/11

1. Install Python 3.11+ from python.org (tick **Add python.exe to PATH**) and Node.js LTS from nodejs.org.
2. In the AccessLoop folder, double-click **`setup_windows.cmd`** (or run it in a terminal). It does not change the
   system's PowerShell execution policy.
3. Start with **`start_windows.cmd`**.

Options: `setup_windows.cmd -AI`, `setup_windows.cmd -Quick`. The scripts set `PYTHONUTF8=1` so the Hindi interface
and reports work on any Windows code page. Line endings of pages are preserved byte for byte on Windows too
(`.gitattributes` keeps HTML, patches and audit logs exactly as committed).

## Docker (any OS, or a shared server)

```bash
docker compose up --build            # http://localhost:8501
```

or without Compose:

```bash
docker build -t accessloop .
docker run --rm -p 127.0.0.1:8501:8501 --shm-size=1g -v accessloop-data:/data accessloop
```

What the image does:

- **Two stages:** axe-core is fetched with `npm ci` (integrity-checked against `package-lock.json`), then copied into a
  slim Python image with the pinned packages and Chromium. Node is not in the final image.
- **Unprivileged:** runs as user `accessloop` (uid 10001), not root.
- **Persistent data on a volume:** `/data/home` holds accounts and signing keys, `/data/workspaces` holds page
  workspaces and their audit logs. Removing the container keeps them; removing the volume deletes them.
- **Health check:** Docker probes Streamlit's `/_stcore/health` every 30 seconds.
- **Local only by default:** Compose binds the port to `127.0.0.1`. To offer it to a team, put it behind the bank's
  reverse proxy with HTTPS and SSO, and change the mapping deliberately.
- **AI optional:** build with `--build-arg WITH_AI=0` to leave the AI packages out entirely. To switch AI on, export the
  variables in the shell before `docker compose up`, never in a file:
  `export ACCESSLOOP_AI=gemini GEMINI_API_KEY=...`

## In CI/CD pipelines (no user interface)

The same engine runs from the command line and fails a build on serious problems:

```bash
python -m accessloop scan site/ --format sarif --out a11y.sarif --fail-on serious   # exit 1 on serious/critical
python -m accessloop fix page.html --out fixed.html --agent --reviewer "Release bot (approved by A. Kumar)"
```

SARIF results show up in GitHub code scanning; `--format junit` suits other CI systems, and Jira/GitHub-issue exports
are also available.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `ACCESSLOOP_HOME` | `~/.accessloop` (`/data/home` in Docker) | Accounts and signing keys |
| `ACCESSLOOP_FOUR_EYES` | off | `1` = maker-checker: a second, different person must approve |
| `ACCESSLOOP_WORKSPACE_TTL_HOURS` | `24` | Page workspaces older than this are cleaned up |
| `ACCESSLOOP_AI` | `off` | `gemini` or `local` (Ollama) for AI drafting |
| `GEMINI_API_KEY` / `GEMINI_MODEL` / `GEMINI_FALLBACK_MODEL` | - | Gemini settings (key only in the shell or a secret store) |
| `OLLAMA_URL` / `OLLAMA_MODEL` | `http://127.0.0.1:11434` / `llama3.1` | Local model; nothing leaves the machine |
| `ACCESSLOOP_AI_TIMEOUT` | `25` | Seconds for the whole AI step, retries included |
| `ACCESSLOOP_CHROMIUM_EXECUTABLE` | Playwright's Chromium | Use a bank-approved Chromium build instead |

## Updating

`git pull`, then run the setup script again (or `docker compose up --build`). Workspaces, accounts and audit logs are
kept.

## Licence

AccessLoop is Apache-2.0 (`LICENSE`, `NOTICE`). Third-party components and their licences are in
`THIRD_PARTY_NOTICES.md`; `python -m accessloop.licenses` prints the exact installed list and CI fails on any strong
copyleft dependency.
