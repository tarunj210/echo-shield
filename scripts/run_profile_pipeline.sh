#!/usr/bin/env bash
set -euo pipefail

IMPORT_JOB_ID="$1"
PROFILE_ID="$2"
INPUT_FILE="$3"

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIPELINE_DIR="$PROJECT_ROOT/ingestion-pipeline"

cd "$PIPELINE_DIR"

source .venv/bin/activate

echo "Starting EchoShield UI-ready pipeline"
echo "Import job: $IMPORT_JOB_ID"
echo "Profile ID: $PROFILE_ID"
echo "Input file: $INPUT_FILE"

python load_watch_history.py \
  --profile-id "$PROFILE_ID" \
  --input-file "$INPUT_FILE" \
  --source google_takeout \
  --import-job-id "$IMPORT_JOB_ID"

python fetch_youtube_metadata.py \
  --profile-id "$PROFILE_ID"

python build_watch_sessions.py \
  --profile-id "$PROFILE_ID" \
  --session-gap-minutes 120

echo "UI-ready pipeline completed successfully"
echo "Dashboard can now load for profile: $PROFILE_ID"

echo "Skipping semantic enrichment in blocking upload pipeline"
echo "Embeddings, similarity edges, clustering, taxonomy mapping, echo scores, and drift will run asynchronously"