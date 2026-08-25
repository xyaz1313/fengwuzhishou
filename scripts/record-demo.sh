#!/usr/bin/env bash
# Record XY Skill plugin marketplace demo GIF
# Usage: ./scripts/record-demo.sh
# Output: demo.gif in repo root
#
# Prerequisites: brew install charmbracelet/tap/vhs gifsicle

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TAPE="$SCRIPT_DIR/demo.tape"
OUTPUT_GIF="$REPO_DIR/demo.gif"

for cmd in vhs gifsicle; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: $cmd not found."
    echo "Install: brew install charmbracelet/tap/vhs gifsicle"
    exit 1
  fi
done

cleanup_plugins() {
  claude plugin uninstall xy@xy-skills 2>/dev/null || true
  claude plugin marketplace remove xy-skills 2>/dev/null || true
}

echo "Cleaning previous plugin state..."
cleanup_plugins

echo "Recording demo..."
rm -f "$OUTPUT_GIF"
(cd "$REPO_DIR" && vhs "$TAPE")

echo "Speeding up 2x..."
cp "$OUTPUT_GIF" /tmp/demo_raw.gif
gifsicle -d2 /tmp/demo_raw.gif "#0-" > "$OUTPUT_GIF"

echo "Cleaning up..."
cleanup_plugins
rm -f /tmp/demo_raw.gif

SIZE=$(du -sh "$OUTPUT_GIF" | awk '{print $1}')
echo "Done: $OUTPUT_GIF ($SIZE)"
