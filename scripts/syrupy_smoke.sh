#!/bin/bash
# Smoke test for syrupy golden-file testing setup.
#
# Verifies:
# 1. syrupy creates a snapshot on first run (--snapshot-update)
# 2. syrupy matches the snapshot on a subsequent run
# 3. Cleanup removes the temporary test file and snapshots
#
# Expected output: "syrupy smoke test passed" at the end, exit 0.

set -e

cat > /tmp/test_syrupy_smoke.py << 'EOF'
def test_smoke(snapshot):
    assert snapshot == "hello"
EOF

cp /tmp/test_syrupy_smoke.py tests/test_syrupy_smoke.py

# First run: create the snapshot
pytest tests/test_syrupy_smoke.py --snapshot-update -q

# Second run: verify the snapshot matches
pytest tests/test_syrupy_smoke.py -v

# Cleanup
rm tests/test_syrupy_smoke.py
rm -rf tests/__snapshots__/test_syrupy_smoke*

echo "syrupy smoke test passed"
