#!/bin/bash
# Wave 1 regression gate: verify all existing examples produce byte-identical output
set -e
BASELINE=".matrixx/baselines/wave1_pre_refactor"
TMP="/tmp/wave1_verify_$$"
mkdir -p "$TMP/rpi" "$TMP/riot" "$TMP/svg" "$TMP/docs" "$TMP/pinmap" "$TMP/json" "$TMP/smauto"

echo "=== RPi regression ==="
FAIL=0
for f in examples/rpi/*.dev; do
    name=$(basename "$f" .dev)
    demol generate rpi "$f" --output-dir "$TMP/rpi/$name" 2>/dev/null
    if ! diff -r "$BASELINE/rpi/$name" "$TMP/rpi/$name" >/dev/null 2>&1; then
        echo "DIFF: $f"
        FAIL=$((FAIL+1))
    fi
done
echo "RPi examples: 40 checked, $FAIL diffs"

echo "=== RIOT regression ==="
FAIL=0
for f in examples/esp/*.dev; do
    name=$(basename "$f" .dev)
    demol generate riot "$f" --output-dir "$TMP/riot/$name" 2>/dev/null
    if ! diff -r "$BASELINE/riot/$name" "$TMP/riot/$name" >/dev/null 2>&1; then
        echo "DIFF: $f"
        FAIL=$((FAIL+1))
    fi
done
echo "RIOT examples: 6 checked, $FAIL diffs"

echo "=== Other backends (multi_periph.dev) ==="
FAIL=0
for f in examples/rpi/multi_periph.dev; do
    name=$(basename "$f" .dev)
    demol generate svg "$f" --output-dir "$TMP/svg/$name" 2>/dev/null
    demol generate docs "$f" --output-dir "$TMP/docs/$name" 2>/dev/null
    demol generate pinmap "$f" --output-dir "$TMP/pinmap/$name" 2>/dev/null
    demol generate json "$f" --output-dir "$TMP/json/$name" 2>/dev/null
    demol generate smauto "$f" --output-dir "$TMP/smauto/$name" 2>/dev/null
    for kind in svg docs pinmap json smauto; do
        if ! diff -r "$BASELINE/$kind/$name" "$TMP/$kind/$name" >/dev/null 2>&1; then
            echo "DIFF: $kind $f"
            FAIL=$((FAIL+1))
        fi
    done
done
echo "Other backends: 5 kinds, $FAIL diffs"

rm -rf "$TMP"
if [ $FAIL -eq 0 ]; then
    echo ""
    echo "SUCCESS: All examples produce byte-identical output"
    exit 0
else
    echo ""
    echo "FAILURE: $FAIL diffs detected"
    exit 1
fi
