#!/usr/bin/env bash
# prepare-release.sh — pre-flight checks before pushing to public GitHub
#
# Run from the repo root:  bash scripts/prepare-release.sh
#
# Exits non-zero if it finds anything that should not ship publicly.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2
FAIL=0

echo "==> Checking for secrets and credential files..."
SECRET_FILES=$(find . -type f \( \
    -name ".env" -o \
    -name "api.txt" -o \
    -name "*credentials*" -o \
    -name "*.pem" -o \
    -name "*.key" \
  \) -not -path "./.git/*" 2>/dev/null)
if [ -n "$SECRET_FILES" ]; then
  echo "  FAIL: credential-shaped files present:"
  echo "$SECRET_FILES" | sed 's/^/    /'
  FAIL=1
else
  echo "  OK: no credential files"
fi

echo "==> Grepping for API key patterns in tracked-eligible files..."
HITS=$(grep -rEnI --include="*.py" --include="*.txt" --include="*.md" \
       --include="*.yaml" --include="*.yml" --include="*.json" \
       --include="*.sh" --include="*.cfg" --include="*.ini" --include="*.toml" \
       "(sk-[a-zA-Z0-9_-]{20,}|AIza[a-zA-Z0-9_-]{30,}|xoxb-[a-zA-Z0-9-]{20,}|ghp_[a-zA-Z0-9]{30,}|AKIA[A-Z0-9]{16}|Bearer [a-zA-Z0-9._-]{20,})" \
       . 2>/dev/null \
       | grep -v -E "(\.git/|__pycache__/)")
if [ -n "$HITS" ]; then
  echo "  FAIL: API-key-shaped strings found:"
  echo "$HITS" | sed 's/^/    /'
  FAIL=1
else
  echo "  OK: no API key patterns"
fi

echo "==> Checking for files > 50 MB (GitHub soft limit)..."
BIG=$(find . -type f -size +50M -not -path "./.git/*" 2>/dev/null)
if [ -n "$BIG" ]; then
  echo "  WARN: files larger than 50 MB (route to Zenodo):"
  echo "$BIG" | sed 's/^/    /'
  FAIL=1
else
  echo "  OK: no files over 50 MB"
fi

echo "==> Checking for files > 100 MB (GitHub hard limit)..."
HUGE=$(find . -type f -size +100M -not -path "./.git/*" 2>/dev/null)
if [ -n "$HUGE" ]; then
  echo "  FAIL: files larger than 100 MB — push will be rejected:"
  echo "$HUGE" | sed 's/^/    /'
  FAIL=1
else
  echo "  OK: no files over 100 MB"
fi

echo "==> Checking for __pycache__ / build artifacts..."
JUNK=$(find . -type d \( -name "__pycache__" -o -name "*.egg-info" -o -name ".pytest_cache" \) -not -path "./.git/*" 2>/dev/null)
if [ -n "$JUNK" ]; then
  echo "  WARN: stale Python artifacts (will be ignored by .gitignore but consider removing):"
  echo "$JUNK" | sed 's/^/    /'
fi

echo "==> Checking .gitignore exists and covers .env..."
if [ ! -f .gitignore ]; then
  echo "  FAIL: no .gitignore"; FAIL=1
elif ! grep -q "^\.env$" .gitignore; then
  echo "  FAIL: .gitignore does not ignore .env"; FAIL=1
else
  echo "  OK: .gitignore present and covers .env"
fi

echo "==> Checking LICENSE files..."
for f in LICENSE LICENSE-DATA CITATION.cff README.md; do
  if [ ! -f "$f" ]; then echo "  FAIL: missing $f"; FAIL=1; else echo "  OK: $f"; fi
done

echo
if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: prepare-release FAILED — fix the issues above before pushing."
  exit 1
fi
echo "RESULT: prepare-release PASSED — safe to commit and push."
