# Third-party software

AccessLoop is licensed under the **Apache License 2.0** (see `LICENSE` and `NOTICE`). It is built on the open-source
components below and uses each of them **unmodified**. None of them is under a strong copyleft licence (GPL, AGPL,
SSPL); CI checks this on every push with `python -m accessloop.licenses`, which reads the licence of every pinned
dependency from its own package metadata and fails the build if a blocker appears.

## Components that do the work

| Component | What AccessLoop uses it for | Licence | Obtained from |
|---|---|---|---|
| axe-core 4.14.0 (Deque Systems) | The accessibility rules engine, injected into the sandboxed page | MPL-2.0 | npm (`package-lock.json`, integrity-checked) |
| Playwright for Python (Microsoft) | Drives the sandboxed browser | Apache-2.0 | PyPI |
| Chromium (The Chromium Authors) | The headless browser that renders and scans pages | BSD-3-Clause and others | downloaded by `playwright install` |
| Streamlit (Snowflake) | The main user interface | Apache-2.0 | PyPI |
| cryptography (PyCA) | Ed25519 signatures on the audit log and evidence | Apache-2.0 OR BSD-3-Clause | PyPI |
| Beautiful Soup 4 | Reading HTML in a few helper paths | MIT | PyPI |
| pytest | Tests | MIT | PyPI |
| google-genai (Google), optional | AI drafting with Gemini, only when switched on | Apache-2.0 | PyPI (`requirements-ai.txt`) |
| pydantic, optional | Used by google-genai | MIT | PyPI |

Transitive Python dependencies (pandas, numpy, pyarrow, requests, Jinja2 and others pulled in by Streamlit) are all
under permissive licences (MIT, BSD, Apache-2.0, PSF) except certifi (MPL-2.0, used unmodified). The full,
version-exact list with licences is produced by:

```bash
python -m accessloop.licenses          # licence table, exit code 1 on a blocker
python -m accessloop.sbom > sbom.cdx.json   # CycloneDX software bill of materials (also built in CI)
```

## What the MPL-2.0 components mean for users

MPL-2.0 is a file-level licence: AccessLoop may be used, sold and combined with proprietary code. If someone modifies
**axe-core's own files** and distributes them, those modified files must be made available under MPL-2.0. AccessLoop
does not modify them; it loads `node_modules/axe-core/axe.min.js` exactly as published, and its source is at
https://github.com/dequelabs/axe-core.

## Services (not software we distribute)

- **Google Gemini API**, optional and off by default: governed by Google's API terms, not by a software licence. Used only
  when an operator sets `ACCESSLOOP_AI=gemini` and gives consent per run; page text is redacted before it is sent.
- **Ollama / local models**, optional: each model has its own licence, chosen by the operator.

## Test pages

Pages under `examples/` were written for this project. Validation used third-party public pages (GOV.UK accessibility
audit page, W3C ACT test cases, MDN) that are fetched for testing and **not redistributed** in this repository except
as derived result numbers.
