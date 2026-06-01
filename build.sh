#!/usr/bin/env bash
# Root-level build script — delegates to scripts/build.sh
# Usage: ./build.sh [--no-cache]
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/scripts/build.sh" "$@"
