#!/bin/sh
# Tag a release after the full test suite passes. Usage: sh scripts/release.sh 0.9.0
set -e
VERSION="$1"
[ -n "$VERSION" ] || { echo "usage: sh scripts/release.sh X.Y.Z"; exit 64; }
grep -q "__version__ = '$VERSION'" accessloop/__init__.py || { echo "accessloop/__init__.py is not $VERSION"; exit 1; }
grep -q "## $VERSION" CHANGELOG.md || { echo "CHANGELOG.md has no entry for $VERSION"; exit 1; }
python -m pytest -q
python -m accessloop.sample_suite --out sample_results
python -m accessloop.sbom > sbom.cdx.json
git add -A && git commit -m "Release $VERSION" || true
git tag -a "v$VERSION" -m "AccessLoop $VERSION"
echo "Tagged v$VERSION. Push with: git push origin main --tags"
echo "Protect the main branch on GitHub: Settings > Branches > Add rule > require pull request reviews and the 'tests' check."
