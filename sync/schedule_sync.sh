#!/bin/bash
# shellcheck disable=SC2181

BRANCH_NAME=${1}
PROJECT_ID=${2}

if [ -z "${BRANCH_NAME}" ] || [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <branch_name> <project_id>"
    exit 1
fi

basedir=$(dirname "$0")
result=0

echo "Generating cloudbuild.json..."
sed "${basedir}"/cloudbuild.json -e "s|__BRANCH_NAME|${BRANCH_NAME}|" > cloudbuild_gen.json

job="${PROJECT_ID}-sync-backup"
echo " + Check if job ${job} exists..."

job_exists=$(gcloud scheduler jobs list --project="${PROJECT_ID}" --quiet | grep "${job}")
if [[ -n "${job_exists}" ]]
then
    echo " + Deleting existing job ${job}..."
    gcloud scheduler jobs delete "${job}" --quiet
fi

echo " + Creating job ${job}..."
gcloud scheduler jobs create http "${job}" \
    --schedule='0 5 * * *' \
    --uri="https://cloudbuild.googleapis.com/v1/projects/${PROJECT_ID}/builds" \
    --message-body-from-file=cloudbuild_gen.json \
    --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform \
    --quiet

if [ $? -ne 0 ]
then
    echo "ERROR scheduling sync job"
    result=1
fi

exit $result
