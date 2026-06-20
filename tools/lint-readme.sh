#!/usr/bin/env bash
# DeMoL README lint gate runner.
# Runs 6 gates: line count, markdownlint, link-check, slop-pattern, image src, alt-text.
# Usage: bash tools/lint-readme.sh [path/to/README.md]
# Default: README.md at repo root.

set -euo pipefail

README="${1:-README.md}"
TOOLS_DIR="$(cd "$(dirname "$0")" && pwd)"
SLOP_LIST="$TOOLS_DIR/slop-patterns.txt"
EXIT=0

gate_pass() { echo "[GATE $1: $2] PASS"; }
gate_fail() { echo "[GATE $1: $2] FAIL: $3"; EXIT=1; }

# GATE 1: line count between 250 and 310
N=$(wc -l < "$README" 2>/dev/null || echo 0)
if [ "$N" -ge 250 ] && [ "$N" -le 310 ]; then
  gate_pass 1 "line-count ($N lines, target 250-310)"
else
  gate_fail 1 "line-count" "$N lines (target 250-310)"
fi

# GATE 2: markdownlint
if npx --yes markdownlint-cli2 "$README" 2>/dev/null; then
  gate_pass 2 "markdownlint"
else
  gate_fail 2 "markdownlint" "see output above"
fi

# GATE 3: markdown-link-check
if npx --yes markdown-link-check "$README" 2>/dev/null; then
  gate_pass 3 "markdown-link-check"
else
  gate_fail 3 "markdown-link-check" "see output above"
fi

# GATE 4: slop-pattern scan (strip comment lines first)
if grep -i -f <(grep -v '^#' "$SLOP_LIST") "$README" >/dev/null 2>&1; then
  MATCHES=$(grep -in -f <(grep -v '^#' "$SLOP_LIST") "$README" || true)
  gate_fail 4 "slop-pattern" "$MATCHES"
else
  gate_pass 4 "slop-pattern"
fi

# GATE 5: image src resolution (skip external URLs)
MISSING=""
while IFS= read -r src; do
  path="${src#src=\"}"
  path="${path%\"}"
  # skip external URLs
  case "$path" in
    http://*|https://*) continue ;;
  esac
  if [ -n "$path" ] && [ ! -f "$path" ] && [ ! -f "assets/$(basename "$path")" ]; then
    MISSING="$MISSING $path"
  fi
done < <(grep -oE 'src="[^"]+"' "$README" || true)
if [ -z "$MISSING" ]; then
  gate_pass 5 "image-src"
else
  gate_fail 5 "image-src" "missing:$MISSING"
fi

# GATE 6: alt-text presence (no empty alts)
if grep -oE '<img[^>]*alt=""' "$README" >/dev/null 2>&1; then
  BAD=$(grep -nE '<img[^>]*alt=""' "$README" || true)
  gate_fail 6 "alt-text" "$BAD"
else
  gate_pass 6 "alt-text"
fi

if [ $EXIT -eq 0 ]; then
  echo ""
  echo "ALL 6 GATES PASS"
else
  echo ""
  echo "SOME GATES FAILED"
fi
exit $EXIT
