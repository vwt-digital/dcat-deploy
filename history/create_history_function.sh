#!/bin/bash

# shellcheck disable=SC2140

PROJECT_ID=${1}
BRANCH_NAME=${2}
SERVICE_ACCOUNT=${3}

echo "Creating topic history function(s)..."

echo " + Cloning pubsub-backup repo..."
git clone --branch="${BRANCH_NAME}" https://github.com/vwt-digital/pubsub-backup.git
(cd pubsub-backup/functions/pubsub-backup && gcloud functions deploy "${PROJECT_ID}-history-func" \
  --entry-point=handler \
  --runtime=python38 \
  --trigger-http \
  --project="${PROJECT_ID}" \
  --region=europe-west1 \
  --memory=512MB \
  --timeout=540s \
  --service-account="${SERVICE_ACCOUNT}" \
  --set-env-vars=PROJECT_ID="${PROJECT_ID}",BRANCH_NAME="${BRANCH_NAME}")

echo " + Setting permissions for ${PROJECT_ID}-history-func..."

cat << EOF > history_func_permissions.json
{ "bindings": [ { "members": [ "serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" ], "role": "roles/cloudfunctions.invoker" } ] }
EOF

gcloud beta functions set-iam-policy "${PROJECT_ID}-history-func" \
  --region=europe-west1 \
  --project="${PROJECT_ID}" \
  history_func_permissions.json
