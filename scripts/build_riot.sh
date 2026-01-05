#!/bin/bash

# Colors for terminal
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DOCKER_IMAGE="riot/riotbuild:latest"
OUTPUT_BASE="build"
WORKSPACE_ROOT=$(pwd)

# Function to print usage
usage() {
    echo "Usage: $0 <model_file.dev> [riot_base_path]"
    echo "Example: $0 examples/esp/wemos_a.dev ~/RIOT"
    exit 1
}

# Check if model file is provided
if [ -z "$1" ]; then
    usage
fi

MODEL_FILE=$1
MODEL_NAME=$(basename "$MODEL_FILE" .dev)
OUTPUT_DIR="$OUTPUT_BASE/$MODEL_NAME"
RIOT_BASE=${2:-$RIOTBASE}

# Detect RIOTBASE if not provided
if [ -z "$RIOT_BASE" ]; then
    if [ -d "$WORKSPACE_ROOT/RIOT" ]; then
        RIOT_BASE="$WORKSPACE_ROOT/RIOT"
    elif [ -d "$HOME/RIOT" ]; then
        RIOT_BASE="$HOME/RIOT"
    fi
fi

echo -e "${BLUE}[*] Verifying RiotOS build for: ${YELLOW}$MODEL_FILE${NC}"

# 1. Generate Code
echo -e "${BLUE}[*] Generating code...${NC}"
mkdir -p "$OUTPUT_DIR"
export PYTHONPATH=$WORKSPACE_ROOT

PYTHON_EXE="python3"
if [ -f "$WORKSPACE_ROOT/venv/bin/python" ]; then
    PYTHON_EXE="$WORKSPACE_ROOT/venv/bin/python"
elif [ -f "$WORKSPACE_ROOT/.venv/bin/python" ]; then
    PYTHON_EXE="$WORKSPACE_ROOT/.venv/bin/python"
fi

$PYTHON_EXE demol/cli/cli.py generate riot "$MODEL_FILE" --output-dir "$OUTPUT_DIR"

if [ $? -ne 0 ]; then
    echo -e "${RED}[!] Code generation failed.${NC}"
    exit 1
fi

# 2. Prepare Docker Command
DOCKER_CMD="docker run --rm -it -v $WORKSPACE_ROOT:/data -w /data/$OUTPUT_DIR"

# Handle RIOTBASE mounting
if [ -n "$RIOT_BASE" ]; then
    RIOT_BASE_ABS=$(realpath "$RIOT_BASE")
    if [[ "$RIOT_BASE_ABS" == "$WORKSPACE_ROOT"* ]]; then
        # Inside workspace
        REL_RIOT_BASE=${RIOT_BASE_ABS#$WORKSPACE_ROOT/}
        MAKE_ARGS="RIOTBASE=/data/$REL_RIOT_BASE"
    else
        # Outside workspace, mount it
        DOCKER_CMD="$DOCKER_CMD -v $RIOT_BASE_ABS:/riot"
        MAKE_ARGS="RIOTBASE=/riot"
    fi
fi

# 3. Run Build
echo -e "${BLUE}[*] Running build in Docker (${YELLOW}$DOCKER_IMAGE${NC})...${NC}"
$DOCKER_CMD $DOCKER_IMAGE make $MAKE_ARGS

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[+] BUILD SUCCESSFUL for $MODEL_NAME${NC}"
else
    echo -e "${RED}[-] BUILD FAILED for $MODEL_NAME${NC}"
    exit 1
fi
