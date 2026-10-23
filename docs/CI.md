# Running AccessLoop in CI

`python -m accessloop scan` returns a non-zero exit code when it finds problems at or above `--fail-on`, and can write
SARIF 2.1.0, which GitHub code scanning (and most CI dashboards) display as annotations on the changed lines.

Copy this into `.github/workflows/accessibility.yml` in your repository:

```yaml
name: Accessibility
on: [pull_request]
permissions:
  contents: read
  security-events: write     # needed to upload SARIF
jobs:
  accessloop:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: |
          python -m pip install -r requirements.txt
          python -m playwright install --with-deps chromium
          npm ci --no-audit --no-fund
      - name: Scan pages
        run: python -m accessloop scan site/ --best-practice --format sarif --out accessloop.sarif --fail-on serious
      - name: Upload results
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: accessloop.sarif, category: accessloop }
```

Unattended fixing in CI is limited on purpose: `fix --approve-auto --reviewer NAME` applies only fixes that need no
typed text, re-verifies each one, writes the repaired copy to a new file, and saves its audit log next to it. Fixes
that need words only a person knows are always left for a reviewer.

## How AccessLoop itself is tested and released

`.github/workflows/tests.yml` runs on every push and pull request:

| Job | What it proves |
|---|---|
| `full-tests` | `pytest` over the engine, fixers, verifier, web server, Streamlit pages (including Streamlit's own AppTest), accounts and signatures, template mapping and a seeded fuzz test of the HTML editor. Then a real-browser smoke test, the **self-check** (`python -m accessloop.selfcheck`: AccessLoop scans its own web UI and Streamlit app in several states and fails on any serious or critical violation), and the sample suite (every fix template proven on real pages). |
| `supply-chain` | `pip-audit` against the pinned `requirements.lock` and `npm audit` for axe-core, then a CycloneDX 1.5 software bill of materials (`python -m accessloop.sbom`) kept as a build artifact. |

Dependencies are pinned: `requirements.lock` (exact versions, regenerated with `scripts/lock.sh`) and
`package-lock.json` (with sha512 integrity hashes). `scripts/release.sh` builds a release zip with checksums.
