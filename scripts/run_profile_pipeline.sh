#!/usr/bin/env bash
set -euo pipefail

IMPORT_JOB_ID="$1"
PROFILE_ID="$2"
INPUT_FILE="$3"

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIPELINE_DIR="$PROJECT_ROOT/ingestion-pipeline"

cd "$PIPELINE_DIR"

source .venv/bin/activate

echo "Starting EchoShield pipeline"
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

#python build_channel_graph.py \
#  --profile-id "$PROFILE_ID" \
#  --session-gap-minutes 120

echo "Graph-ready pipeline completed"

python generate_video_embeddings.py

python build_similarity_edges.py

python discover_semantic_clusters.py

python label_clusters_keybert.py

python dynamic_refine_cluster_labels.py \
  --taxonomy ../config/topic_taxonomy.yml \
  --threshold 0.17 \
  --min-margin 0.02

python map_clusters_to_taxonomy.py

python calculate_echo_chamber_scores.py \
  --profile-id "$PROFILE_ID" \
  --window-days 365 \
  --min-watch-count 5 \
  --min-score 15

python calculate_temporal_drift.py \
  --profile-id "$PROFILE_ID" \
  --granularity weekly \
  --periods 12

python calculate_temporal_drift.py \
  --profile-id "$PROFILE_ID" \
  --granularity monthly \
  --periods 6

echo "EchoShield pipeline completed successfully"