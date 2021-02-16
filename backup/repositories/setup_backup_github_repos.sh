#!/bin/bash

data_catalog_file=${1}
PROJECT_ID=${2}
dest_bucket=${3}
github_secret_id=${4}

if [ -z "${dest_bucket}" ]
then
    echo "Usage: $0 <data_catalog_file> <project_id> <dest_bucket> <github_secret_id>"
    exit 1
fi

basedir=$(dirname "$0")

cp "${data_catalog_file}" "${basedir}"/github_request_backup

cloud_tasks_queue="${PROJECT_ID}-cloudtasks-queue-github-backups"
github_organisations=$(python3 "${basedir}"/list_github_organisations.py "${data_catalog_file}")

#########################################################################
# Retrieve all GitHub organisations from data-catalog
#########################################################################

sed "${basedir}"/cloudbuild_create_backup_tasks.json \
  -e "s|__CLOUD_TASKS_QUEUE__|${cloud_tasks_queue}|" \
  -e "s|__GITHUB_ORGANISATIONS__|${github_organisations}|" > "${basedir}"/cloudbuild_create_backup_tasks_gen.json

#########################################################################
# Deploy GitHub Backup Request function
#########################################################################

gcloud functions deploy "${PROJECT_ID}"-backup-request-func \
  --entry-point=github_request_backup \
  --runtime=python37 \
  --trigger-http \
  --project="${PROJECT_ID}" \
  --region=europe-west1 \
  --max-instances=5 \
  --source="${basedir}"/github_request_backup/ \
  --set-env-vars=PROJECT_ID="${PROJECT_ID}",SECRET_ID="${github_secret_id}",CATALOG_FILE_NAME=data_catalog.json

#########################################################################
# Deploy GitHub Backup Download function
#########################################################################

gcloud functions deploy "${PROJECT_ID}"-backup-download-func \
  --entry-point=github_download_backup \
  --runtime=python37 \
  --trigger-http \
  --project="${PROJECT_ID}" \
  --region=europe-west1 \
  --max-instances=5 \
  --timeout=540 \
  --source="${basedir}"/github_download_backup/ \
  --set-env-vars=PROJECT_ID="${PROJECT_ID}",SECRET_ID="${github_secret_id}",REPO_BACKUP_BUCKET="${dest_bucket}"

#########################################################################
# Set IAM Policies for Cloud Functions
#########################################################################

gcloud functions set-iam-policy "${PROJECT_ID}"-backup-request-func \
  --region=europe-west1 \
  --project="${PROJECT_ID}" config/"${PROJECT_ID}"/repo_backup_func_permissions.json

gcloud functions set-iam-policy "${PROJECT_ID}"-backup-download-func \
  --region=europe-west1 \
  --project="${PROJECT_ID}" config/"${PROJECT_ID}"/repo_backup_func_permissions.json

#########################################################################
# Create Cloud Scheduler for scheduling backups
#########################################################################

# shellcheck disable=SC2216
gcloud scheduler jobs delete "${PROJECT_ID}"-backup-schedule-job --quiet | true
gcloud scheduler jobs create http "${PROJECT_ID}"-backup-schedule-job \
  --schedule='0 2 * * 1-5' \
  --uri="https://cloudbuild.googleapis.com/v1/projects/${PROJECT_ID}/builds" \
  --message-body-from-file="${basedir}"/cloudbuild_create_backup_tasks_gen.json \
  --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com"
