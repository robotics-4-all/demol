#!/usr/bin/env bash
# scripts/test_zephyr_build.sh
#
# Build generated Zephyr applications for the canonical examples against the
# `native_sim` board, asserting that a `zephyr.exe` artifact is produced.
# This is the local replacement for the removed GitHub Actions Zephyr matrix:
# it catches template, devicetree-overlay, Kconfig and CMake regressions that
# pure string/pytest assertions cannot detect.
#
# Usage:
#   scripts/test_zephyr_build.sh                     # canonical smoke subset
#   scripts/test_zephyr_build.sh wemos_srf05         # one example
#   scripts/test_zephyr_build.sh all                 # full example matrix
#   BUILD_ROOT=build/alt scripts/test_zephyr_build.sh wemos_bme280
#
# Requirements: `west` on PATH (auto-installed via pip if missing), a Zephyr
# workspace (auto-initialised at $WEST_WORKSPACE if missing), host build deps
# (cmake, ninja, gperf, dtc), and `demol` importable in the active Python.
# Builds use the host toolchain (ZEPHYR_TOOLCHAIN_VARIANT=host) so no Zephyr
# SDK download is required.
#
# Output files live under ${BUILD_ROOT:-build/zephyr_test}/<example>/ and the
# west build dirs are removed on success unless KEEP_BUILD=1 is set.
#
# Environment overrides:
#   WEST_WORKSPACE   Zephyr workspace root        (default: ~/zephyrproject)
#   ZEPHYR_REV       manifest revision to init    (default: v3.5-branch)
#   ZEPHYR_BOARD     west build board             (default: native_sim)
#   BUILD_ROOT       generated-output root        (default: build/zephyr_test)
#   KEEP_BUILD=1     keep build dirs and outputs

set -euo pipefail

# Smoke subset: one example per driver class (upstream I2C sensor, custom
# GPIO bit-bang, trigger-echo, CONSTRAINT + custom I2C). Mirrors the matrix
# the removed CI workflow used on pull requests.
CANONICAL_EXAMPLES=(
    wemos_bme280
    wemos_dht22
    wemos_srf05
    wemos_constraint_bme680
)
ALL_EXAMPLES=(
    esp_bme680
    esp_iot_device
    wemos_bh1750
    wemos_bme280
    wemos_button
    wemos_constraint_bme680
    wemos_dht22
    wemos_ds18b20
    wemos_mqtt_bme680
    wemos_pir_hcsr501
    wemos_sampling_bme680
    wemos_srf05
    wemos_bme680
)
EXAMPLES_DIR="examples/esp"
BUILD_ROOT="${BUILD_ROOT:-build/zephyr_test}"
WEST_WORKSPACE="${WEST_WORKSPACE:-$HOME/zephyrproject}"
ZEPHYR_REV="${ZEPHYR_REV:-v3.5-branch}"
ZEPHYR_BOARD="${ZEPHYR_BOARD:-native_sim}"
KEEP_BUILD="${KEEP_BUILD:-0}"

# Allow explicit example list, `all`, otherwise the canonical subset.
if [[ $# -gt 0 ]]; then
    if [[ "$1" == "all" ]]; then
        examples=("${ALL_EXAMPLES[@]}")
    else
        examples=("$@")
    fi
else
    examples=("${CANONICAL_EXAMPLES[@]}")
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
NC='\033[0m'

log()  { echo -e "$@"; }
fail() { log "${RED}  ✗${NC} $1"; return 0; }  # non-fatal: caller counts and continues
pass() { log "${GREEN}  ✓${NC} $1"; }

cleanup_build() {
    local dir="$1"
    [[ -d "$dir" ]] || return 0
    chmod -R u+rwX "$dir" 2>/dev/null || true
    rm -rf "$dir" 2>/dev/null || \
        log "${YELLOW}    warn: could not fully clean $dir${NC}"
}

# ── Pre-flight ──────────────────────────────────────────────────────────────
if ! python3 -c 'import demol' >/dev/null 2>&1; then
    log "${RED}Error${NC}: 'demol' is not importable. Activate a venv that has"
    log "the package installed (e.g. 'pip install -e .') and retry."
    exit 2
fi

if [[ ! -d "$EXAMPLES_DIR" ]]; then
    log "${RED}Error${NC}: $EXAMPLES_DIR/ not found; run from the repo root."
    exit 2
fi

missing_deps=()
for dep in cmake ninja gperf dtc; do
    command -v "$dep" >/dev/null 2>&1 || missing_deps+=("$dep")
done
if [[ ${#missing_deps[@]} -gt 0 ]]; then
    log "${RED}Error${NC}: missing host build dependencies: ${missing_deps[*]}"
    log "Install them, e.g. on Debian/Ubuntu:"
    log "  sudo apt-get install -y cmake ninja-build gperf device-tree-compiler \\"
    log "       gcc gcc-multilib g++-multilib libsdl2-dev libmagic1"
    exit 2
fi

if ! command -v west >/dev/null 2>&1; then
    log "${YELLOW}==>${NC} west not on PATH; installing via pip --user"
    python3 -m pip install --user --quiet west
    export PATH="$HOME/.local/bin:$PATH"
    command -v west >/dev/null 2>&1 || { log "${RED}Error${NC}: west still not found after install"; exit 2; }
fi

# ── Workspace init (idempotent, mirrors the former CI job) ─────────────────
if [[ ! -d "$WEST_WORKSPACE/.west" ]]; then
    log "${CYAN}==>${NC} Initialising Zephyr workspace at $WEST_WORKSPACE ($ZEPHYR_REV)"
    mkdir -p "$(dirname "$WEST_WORKSPACE")"
    west init -m https://github.com/zephyrproject-rtos/zephyr \
              --mr "$ZEPHYR_REV" "$WEST_WORKSPACE"
    ( cd "$WEST_WORKSPACE" && west update )
else
    log "${CYAN}==>${NC} Reusing Zephyr workspace at $WEST_WORKSPACE"
fi

if [[ -f "$WEST_WORKSPACE/zephyr/scripts/requirements.txt" ]]; then
    python3 -m pip install --quiet -r "$WEST_WORKSPACE/zephyr/scripts/requirements.txt"
fi

mkdir -p "$BUILD_ROOT"

total=${#examples[@]}
passed=0
failed=0
failed_names=()

log ""
log "${CYAN}== Zephyr build gate ==${NC}  (board=$ZEPHYR_BOARD, $total example(s), output: $BUILD_ROOT)"
log ""

for i in "${!examples[@]}"; do
    example="${examples[$i]}"
    n=$((i + 1))
    out_dir="$BUILD_ROOT/$example"
    build_dir="$WEST_WORKSPACE/build-$example"
    dev="$EXAMPLES_DIR/$example.dev"

    log "[$n/$total] ${CYAN}${example}${NC}"

    if [[ ! -f "$dev" ]]; then
        fail "model not found: $dev"
        failed=$((failed + 1))
        failed_names+=("$example")
        continue
    fi

    cleanup_build "$out_dir"
    cleanup_build "$build_dir"
    mkdir -p "$out_dir"

    if ! python3 -m demol.cli.cli generate zephyr "$dev" --output-dir "$out_dir" \
            --board "$ZEPHYR_BOARD" >"$out_dir/codegen.log" 2>&1; then
        fail "codegen failed (see $out_dir/codegen.log)"
        failed=$((failed + 1))
        failed_names+=("$example")
        continue
    fi

    if [[ ! -f "$out_dir/app/CMakeLists.txt" ]]; then
        fail "missing generated app/CMakeLists.txt"
        failed=$((failed + 1))
        failed_names+=("$example")
        continue
    fi

    # Canonical Zephyr layout: the application lives inside the west workspace
    # so `west build` resolves ZEPHYR_BASE and the module list. Each example
    # gets its own app dir + build dir so runs cannot clobber one another.
    app_dir="$WEST_WORKSPACE/app-$example"
    rm -rf "$app_dir"
    cp -r "$out_dir/app" "$app_dir"

    if ! ( cd "$WEST_WORKSPACE" && \
           ZEPHYR_TOOLCHAIN_VARIANT=host \
           west build -b "$ZEPHYR_BOARD" -d "$build_dir" "$app_dir" ) \
            >"$out_dir/build.log" 2>&1; then
        log "${RED}    last 10 lines of $out_dir/build.log:${NC}"
        tail -n 10 "$out_dir/build.log" | sed 's/^/      /'
        fail "build failed"
        failed=$((failed + 1))
        failed_names+=("$example")
        continue
    fi

    exe="$build_dir/zephyr/zephyr.exe"
    if [[ ! -f "$exe" ]]; then
        fail "no zephyr.exe under $build_dir/zephyr/"
        failed=$((failed + 1))
        failed_names+=("$example")
        continue
    fi

    size=$(stat -c%s "$exe")
    pass "$example  →  zephyr.exe  (board=$ZEPHYR_BOARD, $((size / 1024)) KiB)"
    passed=$((passed + 1))

    if [[ "$KEEP_BUILD" != "1" ]]; then
        cleanup_build "$build_dir"
        rm -rf "$app_dir"
        cleanup_build "$out_dir"
    fi
done

log ""
if [[ $failed -eq 0 ]]; then
    log "${CYAN}== result ==${NC}  ${GREEN}${passed} passed${NC} / 0 failed"
else
    log "${CYAN}== result ==${NC}  ${GREEN}${passed} passed${NC} / ${RED}${failed} failed${NC}"
fi

if [[ $failed -gt 0 ]]; then
    log ""
    log "${YELLOW}Failed examples${NC}: ${failed_names[*]}"
    exit 1
fi
