#!/bin/bash

# =================================================================
# STEP 1: CONFIGURATION - Fill these in
# =================================================================

# Your Google Cloud Project ID
export PROJECT_ID="clout-estate"

# The Google Cloud region for your deployment
export REGION="us-central1" # <--- FILLED IN

# The name of your service on Cloud Run
export SERVICE_NAME="codex-orchestrator"

# The full path for your Docker image in Google Artifact Registry
export IMAGE_LOCATION="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# The email of the Service Account we created earlier
export SA_EMAIL="codex-orchestrator-sa@$PROJECT_ID.iam.gserviceaccount.com"

# The name of your API key secret in Secret Manager
export API_KEY_SECRET_NAME="CODEX_API_KEY" # <--- FILLED IN

# (Optional) The name of your database URL secret, if you have one
# export DATABASE_URL_SECRET_NAME="[DATABASE_URL_SECRET]"


# =================================================================
# STEP 2: BUILD & PUSH THE DOCKER IMAGE
# =================================================================

# This command uses Google Cloud Build to create your Docker image
# It automatically pushes the finished image to your Artifact Registry
echo "Building and pushing Docker image..."
gcloud builds submit --tag "$IMAGE_LOCATION"


# =================================================================
# STEP 3: DEPLOY TO CLOUD RUN
# =================================================================

# This is the final deployment command.
# It wires up your service account, secrets, and other settings.
echo "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_LOCATION" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --service-account="$SA_EMAIL" \
  --update-secrets=CODEX_API_KEY="$API_KEY_SECRET_NAME":latest

  # --- If you have a DATABASE_URL secret, uncomment the line below ---
  # --update-secrets=CODEX_API_KEY=$API_KEY_SECRET_NAME:latest,DATABASE_URL=$DATABASE_URL_SECRET_NAME:latest

echo "Deployment complete."
echo "You can find your service URL in the Google Cloud Console."
