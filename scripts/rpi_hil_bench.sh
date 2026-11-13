#!/usr/bin/env bash
# L4 hardware-in-the-loop bench: run on a real Raspberry Pi 3/4.
# Generates the device, starts it with docker compose, and asserts that the
# configured broker actually receives readings on the expected topic.
set -euo pipefail

MODEL=""
BROKER_HOST=""
BROKER_PORT="1883"
TOPIC=""
EXPECT="5"
TIMEOUT="30"
OUTPUT_DIR=""
KEEP="0"
MOSQUITTO_IMAGE="${MOSQUITTO_IMAGE:-eclipse-mosquitto:2.0.20}"

usage() {
    cat <<'USAGE'
Usage: rpi_hil_bench.sh --model MODEL.dev --broker-host HOST --topic TOPIC [options]

Options:
  --broker-port PORT   Broker port (default: 1883)
  --expect N           Minimum messages to receive (default: 5)
  --timeout SECONDS    Subscriber timeout (default: 30)
  --output-dir DIR     Generation directory (default: mktemp)
  --keep               Keep the work directory and containers on exit
  --help               Show this message
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL="${2:-}"; shift 2 ;;
        --broker-host) BROKER_HOST="${2:-}"; shift 2 ;;
        --broker-port) BROKER_PORT="${2:-}"; shift 2 ;;
        --topic) TOPIC="${2:-}"; shift 2 ;;
        --expect) EXPECT="${2:-}"; shift 2 ;;
        --timeout) TIMEOUT="${2:-}"; shift 2 ;;
        --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
        --keep) KEEP="1"; shift ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ -z "$MODEL" || -z "$BROKER_HOST" || -z "$TOPIC" ]]; then
    echo "--model, --broker-host and --topic are required" >&2
    usage >&2
    exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required on the bench host" >&2
    exit 1
fi
if [[ ! -f "$MODEL" ]]; then
    echo "model not found: $MODEL" >&2
    exit 1
fi

# Validate numeric arguments before they reach arithmetic evaluation or CLI flags.
if ! [[ "$BROKER_PORT" =~ ^[0-9]{1,5}$ ]]; then
    echo "--broker-port must be an integer" >&2; exit 2
fi
if ! [[ "$EXPECT" =~ ^[0-9]+$ ]]; then
    echo "--expect must be a non-negative integer" >&2; exit 2
fi
if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
    echo "--timeout must be a non-negative integer" >&2; exit 2
fi
if [[ -n "$OUTPUT_DIR" && ( "$OUTPUT_DIR" == "/" || "$OUTPUT_DIR" == "." || "$OUTPUT_DIR" == ".." ) ]]; then
    echo "refusing unsafe --output-dir: $OUTPUT_DIR" >&2; exit 2
fi

if [[ -n "$OUTPUT_DIR" ]]; then
    WORKDIR="$OUTPUT_DIR"
    CREATED_WORKDIR="0"
else
    WORKDIR="$(mktemp -d /tmp/demol-hil.XXXXXX)"
    CREATED_WORKDIR="1"
fi
mkdir -p "$WORKDIR"
cleanup() {
    if [[ "$KEEP" == "1" ]]; then
        echo "keeping work directory: $WORKDIR"
        return
    fi
    (cd "$WORKDIR" && docker compose down -v --remove-orphans >/dev/null 2>&1 || true)
    # Only delete a directory this script created; never a user-supplied path.
    if [[ "$CREATED_WORKDIR" == "1" ]]; then
        rm -rf -- "$WORKDIR"
    else
        echo "leaving user-supplied --output-dir in place: $WORKDIR"
    fi
}
trap cleanup EXIT

echo "[1/4] generating RPi code from $MODEL"
if command -v demol >/dev/null 2>&1; then
    demol generate rpi "$MODEL" --output-dir "$WORKDIR"
else
    python3 -m demol.cli.cli generate rpi "$MODEL" --output-dir "$WORKDIR"
fi

echo "[2/4] building and starting containers"
(cd "$WORKDIR" && docker compose up -d --build)

echo "[3/4] subscribing to $TOPIC on $BROKER_HOST:$BROKER_PORT"
SUB_LOG="$WORKDIR/subscriber.log"
set +e
docker run --rm --network host "$MOSQUITTO_IMAGE" \
    mosquitto_sub -h "$BROKER_HOST" -p "$BROKER_PORT" -t "$TOPIC" -C "$EXPECT" -W "$TIMEOUT" -v \
    >"$SUB_LOG" 2>&1
SUB_RC=$?
set -e

COUNT=$(wc -l <"$SUB_LOG" | tr -d ' ')
echo "[4/4] received $COUNT message(s) (subscriber rc=$SUB_RC)"

if [[ "$COUNT" -lt "$EXPECT" ]]; then
    echo "FAIL: expected at least $EXPECT messages on '$TOPIC'" >&2
    echo "--- subscriber output ---" >&2
    cat "$SUB_LOG" >&2
    echo "--- container state ---" >&2
    (cd "$WORKDIR" && docker compose ps) >&2 || true
    echo "--- container logs ---" >&2
    (cd "$WORKDIR" && docker compose logs --tail=50) >&2 || true
    exit 1
fi

echo "PASS: generated device delivered readings to $BROKER_HOST:$BROKER_PORT/$TOPIC"
head -n 3 "$SUB_LOG"
