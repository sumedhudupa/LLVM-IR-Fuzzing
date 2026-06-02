#!/usr/bin/env bash
# Root-level run script — delegates to scripts/run.sh
# Usage: ./run.sh [--eval | --stop | --logs]
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/scripts/run.sh" "$@"
