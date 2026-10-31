#!/usr/bin/env bash
# Package source + pinned runtime dependencies for the arm64 / Python 3.12 Lambda runtime.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/build/lambda"
PYTHON="${PYTHON:-python3}"

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" -m pip install --quiet \
  --platform manylinux2014_aarch64 --implementation cp --python-version 3.12 \
  --only-binary=:all: --target "$OUT" -r "$ROOT/requirements.txt"

cp -r "$ROOT/src/slack_rag" "$OUT/"
find "$OUT" -name "__pycache__" -type d -prune -exec rm -rf {} +
echo "Built $OUT"
