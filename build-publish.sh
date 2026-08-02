#!/bin/bash
# Build and publish package to PyPI, then tag the release in git
# Activates virtual environment before running
set -e

# Activate virtual environment
source bin/activate

# Refuse to publish uncommitted code — the tag below must point at the
# commit that actually produced the artifacts
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Working tree is not clean; commit before publishing."
    exit 1
fi

VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
INIT_VERSION=$(python -c "import byteforge_telegram; print(byteforge_telegram.__version__)")

# pyproject.toml and __init__.py must agree before anything is published
if [ "$VERSION" != "$INIT_VERSION" ]; then
    echo "❌ Version mismatch: pyproject.toml has ${VERSION} but __init__.py has ${INIT_VERSION}."
    exit 1
fi

# Check the tag BEFORE uploading — a tag collision discovered after twine
# upload leaves an unrecoverable published-but-untagged state
if git rev-parse -q --verify "refs/tags/v${VERSION}" >/dev/null; then
    echo "❌ Tag v${VERSION} already exists; bump the version before publishing."
    exit 1
fi

# Clean previous builds
rm -rf dist/*

# Build package
python -m build

# Upload to PyPI
python -m twine upload dist/*

# Tag the release so PyPI and git can't drift (a version bump is not a
# release until the tag exists)
git tag -a "v${VERSION}" -m "Release ${VERSION}"
git push origin "v${VERSION}"
echo "✅ Published and tagged v${VERSION}"
