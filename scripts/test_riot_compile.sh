#!/usr/bin/env bash
# scripts/test_riot_compile.sh
#
# Compile generated RIOT firmware for the canonical wemos examples and
# assert that a .elf artifact is produced. This is the local-CI
# equivalent of the GitHub Actions `riot-build` matrix job; running it
# before pushing catches template regressions (missing #includes,
# undeclared functions, unused variables) that pytest cannot detect.
#
# Usage:
#   scripts/test_riot_compile.sh                  # all 4 canonical examples
#   scripts/test_riot_compile.sh wemos_bme680    # one example
#   BUILD_ROOT=build/alt scripts/test_riot_compile.sh wemos_srf05
#
# Requirements: Docker (~30s per example with cached image), `demol`
# importable in the active Python. Exits non-zero if any example fails.
#
# Output files live under ${BUILD_ROOT:-build/riot_test}/<example>/bin/
# and are removed on success unless KEEP_BUILD=1 is set.

set -euo pipefail

CANONICAL_EXAMPLES=(
    esp_bme280
    wemos_bme680
    wemos_bme680_alert
    wemos_button
    wemos_srf05
)
EXAMPLES_DIR="examples/esp"
BUILD_ROOT="${BUILD_ROOT:-build/riot_test}"
KEEP_BUILD="${KEEP_BUILD:-0}"

# Allow explicit example list, otherwise the canonical four.
if [[ $# -gt 0 ]]; then
    examples=("$@")
else
    examples=("${CANONICAL_EXAMPLES[@]}")
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
NC='\033[0m'

log()  { echo -e "$@"; }
fail() { log "${RED}  ✗${NC} $1"; return 1; }
pass() { log "${GREEN}  ✓${NC} $1"; }

# build_docker.sh bind-mounts the output dir into a container that runs
# as root, so generated files are owned by root with no write perm for
# the host user. chmod first, then rm; if even chmod fails (e.g. user
# is not root), warn and continue rather than aborting the whole gate.
cleanup_build() {
    local dir="$1"
    [[ -d "$dir" ]] || return 0
    chmod -R u+rwX "$dir" 2>/dev/null || true
    rm -rf "$dir" 2>/dev/null || \
        log "${YELLOW}    warn: could not fully clean $dir (root-owned files from Docker; run 'sudo rm -rf' to clear)${NC}"
}

# ── Pre-flight ──────────────────────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
    log "${RED}Error${NC}: docker is not on PATH. The RIOT build runs in a"
    log "self-contained Docker image (riot/riotbuild); install Docker or run"
    log "the build on a host that has it."
    exit 2
fi

if ! python3 -c 'import demol' >/dev/null 2>&1; then
    log "${RED}Error${NC}: 'demol' is not importable. Activate a venv that has"
    log "the package installed (e.g. 'pip install -e .') and retry."
    exit 2
fi

if [[ ! -d "$EXAMPLES_DIR" ]]; then
    log "${RED}Error${NC}: $EXAMPLES_DIR/ not found; run from the repo root."
    exit 2
fi

mkdir -p "$BUILD_ROOT"

total=${#examples[@]}
passed=0
failed=0
failed_names=()

log ""
log "${CYAN}== RIOT compile gate ==${NC}  ($total example(s), output: $BUILD_ROOT)"
log ""

for i in "${!examples[@]}"; do
    example="${examples[$i]}"
    n=$((i + 1))
    out_dir="$BUILD_ROOT/$example"
    dev="$EXAMPLES_DIR/$example.dev"

    log "[$n/$total] ${CYAN}${example}${NC}"

    if [[ ! -f "$dev" ]]; then
        fail "model not found: $dev"
        failed=$((failed + 1))
        failed_names+=("$example")
        continue
    fi

    cleanup_build "$out_dir"
    mkdir -p "$out_dir"

    if ! python3 -m demol.cli.cli generate riot "$dev" --output-dir "$out_dir" \
            >"$out_dir/codegen.log" 2>&1; then
        fail "codegen failed (see $out_dir/codegen.log)"
        failed=$((failed + 1))
        failed_names+=("$example")
        continue
    fi

    for f in Dockerfile.riotbuild build_docker.sh Makefile main.c; do
        if [[ ! -f "$out_dir/$f" ]]; then
            fail "missing generated file: $f"
            failed=$((failed + 1))
            failed_names+=("$example")
            continue 2
        fi
    done

    if ! ( cd "$out_dir" && ./build_docker.sh ) \
            >"$out_dir/build.log" 2>&1; then
        log "${RED}    last 10 lines of $out_dir/build.log:${NC}"
        tail -n 10 "$out_dir/build.log" | sed 's/^/      /'
        fail "build failed"
        failed=$((failed + 1))
        failed_names+=("$example")
        continue
    fi

    board=$(grep -m1 '^BOARD ?=' "$out_dir/Makefile" | sed 's/.*= *//')
    shopt -s nullglob
    elfs=("$out_dir"/bin/"$board"/*.elf)
    shopt -u nullglob
    if [[ ${#elfs[@]} -eq 0 ]]; then
        fail "no .elf under $out_dir/bin/$board/"
        failed=$((failed + 1))
        failed_names+=("$example")
        continue
    fi

    elf="${elfs[0]}"
    size=$(stat -c%s "$elf")
    pass "$example  →  $(basename "$elf")  (board=$board, $((size / 1024)) KiB)"
    passed=$((passed + 1))

    if [[ "$KEEP_BUILD" != "1" ]]; then
        cleanup_build "$out_dir"
    fi
done

log ""
log "${CYAN}== result ==${NC}  ${GREEN}${passed} passed${NC} / ${failed:+${RED}${failed} failed${NC} }${failed:-(none failed)}"

if [[ $failed -gt 0 ]]; then
    log ""
    log "${YELLOW}Failed examples${NC}: ${failed_names[*]}"
    exit 1
fi
