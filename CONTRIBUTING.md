# Working on AccessLoop together

## One-time setup (each teammate)
```bash
git clone https://github.com/<owner>/AccessLoop.git
cd AccessLoop
bash setup_mac.sh            # or setup_linux.sh / setup_windows.cmd: venv, pinned packages, Chromium, axe-core, tests, smoke
```

## Daily loop
```bash
git checkout main && git pull            # start from the latest main
git checkout -b feat/<short-name>        # one branch per task, e.g. feat/button-no-id
# ...edit...
python -m pytest -q                      # unit tests (fast)
python -m accessloop.sample_suite        # real-browser acceptance (8 cases)
git add -A && git commit -m "Add <what>"
git push -u origin feat/<short-name>     # then open a Pull Request on GitHub
```
Teammate reviews the PR, CI must be green, then **Squash and merge**. Delete the branch.

## Rules that keep us out of each other's way
- Never commit straight to `main`; always a branch + PR.
- Split work by file where possible:
  - Engine / agent logic: `accessloop/planner.py`, `workflow.py`, `verification.py`
  - UI / demo: `app.py`, `docs/DEMO_SCRIPT.md`
  - Tests / samples: `tests/`, `examples/samples/`
- Pull `main` into your branch before opening a PR if it's more than a few hours old: `git pull origin main`.
- Every new fix template needs: a sample page in `examples/samples/`, a case in `accessloop/sample_suite.py`, and a unit test.
- Never commit `.env`, API keys, `.venv/`, `node_modules/` or `sample_results/` (already in `.gitignore`).

## Licence of contributions
By contributing you agree that your contribution is licensed under the Apache License 2.0, like the rest of AccessLoop.
New dependencies must not be GPL/AGPL/SSPL; `python -m accessloop.licenses` (run in CI) checks this.
