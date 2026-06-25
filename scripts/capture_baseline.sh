#!/bin/bash
set -e
BASELINE=".matrixx/baselines/wave1_pre_refactor"
mkdir -p "$BASELINE/rpi" "$BASELINE/riot"

echo "Capturing RPi baseline..."
for f in examples/rpi/*.dev; do
    name=$(basename "$f" .dev)
    demol generate rpi "$f" --output-dir "$BASELINE/rpi/$name" 2>/dev/null
done

echo "Capturing RIOT baseline..."
for f in examples/esp/*.dev; do
    name=$(basename "$f" .dev)
    demol generate riot "$f" --output-dir "$BASELINE/riot/$name" 2>/dev/null
done

# Generate docs, svg, pinmap, json, smauto for rpi examples
echo "Capturing other backend baselines..."
for f in examples/rpi/multi_periph.dev; do
    name=$(basename "$f" .dev)
    demol generate docs "$f" --output-dir "$BASELINE/docs/$name" 2>/dev/null || true
    demol generate svg "$f" --output-dir "$BASELINE/svg/$name" 2>/dev/null || true
    demol generate pinmap "$f" --output-dir "$BASELINE/pinmap/$name" 2>/dev/null || true
    demol generate json "$f" --output-dir "$BASELINE/json/$name" 2>/dev/null || true
    demol generate smauto "$f" --output-dir "$BASELINE/smauto/$name" 2>/dev/null || true
done

echo "Baseline complete"
ls -la "$BASELINE/"
