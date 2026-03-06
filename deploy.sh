#!/bin/bash
# deploy.sh — automated Cloud Run deployment for MeetMind
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# Requirements:
#   - Google Cloud CLI installed and authenticated (gcloud auth login)
#   - GOOGLE_API_KEY set in your environment or .env file

set -e

# ── Config ──────────────────────────────────────────────────────────────────
PROJECT_ID="meetmind-488903"
SERVICE_NAME="meetmind"
REGION="us-central1"
SOURCE_DIR="./app"

# ── Validate API key ─────────────────────────────────────────────────────────
if [ -z "$GOOGLE_API_KEY" ]; then
  if [ -f "$SOURCE_DIR/.env" ]; then
    export $(grep -v '^#' "$SOURCE_DIR/.env" | xargs)
  fi
fi

if [ -z "$GOOGLE_API_KEY" ]; then
  echo "Error: GOOGLE_API_KEY is not set."
  echo "Set it in your environment or in app/.env before deploying."
  exit 1
fi

echo "Deploying MeetMind to Cloud Run..."
echo "Project : $PROJECT_ID"
echo "Region  : $REGION"
echo "Service : $SERVICE_NAME"
echo ""

# ── Set project ──────────────────────────────────────────────────────────────
gcloud config set project "$PROJECT_ID"

# ── Enable required APIs ─────────────────────────────────────────────────────
echo "Enabling Cloud Run and Cloud Build APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# ── Deploy ───────────────────────────────────────────────────────────────────
echo "Building and deploying..."
gcloud run deploy "$SERVICE_NAME" \
  --source "$SOURCE_DIR" \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "Deployment complete."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format "value(status.url)")
echo "Live at: $SERVICE_URL"
