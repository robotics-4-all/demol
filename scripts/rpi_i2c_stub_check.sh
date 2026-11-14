#!/usr/bin/env bash
# L3 (kernel-level) I2C emulation: exposes a stub i2c adapter with seeded
# registers so real smbus2/vendor drivers can be exercised without hardware.
# Requires root and the i2c-stub kernel module; Linux x86 or Raspberry Pi.
set -euo pipefail

CHIP_ADDR="${1:-0x76}"
REGISTER="${2:-0xd0}"
VALUE="${3:-0x61}"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "must run as root (modprobe/i2cset)" >&2
    exit 1
fi
if ! command -v modprobe >/dev/null 2>&1; then
    echo "modprobe not found; install kmod" >&2
    exit 1
fi

for arg in "$CHIP_ADDR" "$REGISTER" "$VALUE"; do
    if ! [[ "$arg" =~ ^0[xX][0-9a-fA-F]{1,4}$ ]]; then
        echo "expected hex values like 0x76, got: $arg" >&2
        exit 2
    fi
done

LOADED_BY_US="0"
cleanup() {
    if [[ "$LOADED_BY_US" == "1" ]]; then
        modprobe -r i2c_stub 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Only unload a stub the script loaded itself; never disturb an existing adapter.
if ! lsmod | awk '{print $1}' | grep -qx i2c_stub; then
    modprobe i2c_stub chip_addr="$CHIP_ADDR"
    LOADED_BY_US="1"
else
    echo "i2c_stub already loaded; leaving it loaded on exit" >&2
fi

BUS=$(i2cdetect -l | awk '/SMBus stub driver/ {print $1; exit}' | sed 's/^i2c-//')
if [[ -z "$BUS" ]]; then
    echo "could not find the i2c-stub adapter" >&2
    exit 1
fi

i2cset -y "$BUS" "$CHIP_ADDR" "$REGISTER" "$VALUE"

DEMOL_I2C_BUS="$BUS" DEMOL_I2C_ADDR="$CHIP_ADDR" DEMOL_I2C_REG="$REGISTER" DEMOL_I2C_SEED="$VALUE" python3 - <<'PY'
import os

from smbus2 import SMBus

bus_id = int(os.environ["DEMOL_I2C_BUS"])
addr = int(os.environ["DEMOL_I2C_ADDR"], 0)
register = int(os.environ["DEMOL_I2C_REG"], 0)

with SMBus(bus_id) as bus:
    value = bus.read_byte_data(addr, register)

print(f"i2c-{bus_id} addr=0x{addr:02x} reg=0x{register:02x} -> 0x{value:02x}")
assert value == int(os.environ["DEMOL_I2C_SEED"], 0), (value, os.environ["DEMOL_I2C_SEED"])
PY

echo "PASS: i2c-stub adapter i2c-$BUS answered register reads for 0x${CHIP_ADDR#0x}"
echo "Generated drivers pin bus 1 by default; use an adapter numbered 1 or adapt the driver for a full run."
