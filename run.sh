#!/usr/bin/env bash
# Runs an arbitrary note file through the dockerised pipeline. The input
# path is a real argument — not baked into docker-compose.yml — because the
# grader points this at a file we've never seen.
set -euo pipefail

INPUT="${1:?usage: run.sh <input-path> [output-path]}"
OUTPUT="${2:-output.jsonl}"

mkdir -p "$(dirname "$OUTPUT")"

INPUT_DIR="$(cd "$(dirname "$INPUT")" && pwd)"
INPUT_NAME="$(basename "$INPUT")"
OUTPUT_DIR="$(cd "$(dirname "$OUTPUT")" && pwd)"
OUTPUT_NAME="$(basename "$OUTPUT")"

docker compose run --rm \
  -v "$INPUT_DIR:/input:ro" \
  -v "$OUTPUT_DIR:/output" \
  coder --input "/input/$INPUT_NAME" --output "/output/$OUTPUT_NAME"

echo "wrote $OUTPUT"
