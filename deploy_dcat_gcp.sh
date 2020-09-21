#!/bin/bash

# This scripts deploys the data management (datasets, backup, clean up, ...) of the specified data catalog to GCP

data_catalog_path=${1}
PROJECT_ID=${2}
BRANCH_NAME=${3}
GITHUB_SECRET_ID=${4}
SERVICE_ACCOUNT=${5}

SCHEMAS_FOLDER=""
if [ -n "${6}" ]
then
    SCHEMAS_FOLDER=${6}
fi

SCHEMAS_CONFIG=""
if [ -n "${7}" ]
then
    SCHEMAS_CONFIG=${7}
fi

echo "Schemas folder: ${SCHEMAS_FOLDER}"
echo "Schemas config: ${SCHEMAS_CONFIG}"

dcat_deploy_dir=$(dirname "$0")

if [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <data_catalog_path> <PROJECT_ID> <BRANCH_NAME> [GITHUB_SECRET_ID]"
    exit 1
fi

############################################################
# Create and configure github repos
############################################################

if [ -n "${GITHUB_SECRET_ID}" ]
then
    "${dcat_deploy_dir}"/catalog/repos/create_github_repos.sh "${data_catalog_path}" "${GITHUB_SECRET_ID}"
fi

############################################################
# Deploy datasets using deployment manager
############################################################

"${dcat_deploy_dir}"/catalog/scripts/deploy_data_catalog.sh "${PROJECT_ID}"-dcat-deploy "${data_catalog_path}" "${PROJECT_ID}" "${BRANCH_NAME}" "${SCHEMAS_FOLDER}" "${SCHEMAS_CONFIG}"

if [ $? -ne 0 ]
then
    echo "ERROR deploying data catalog"
    exit 1
fi

############################################################
# Schedule backup job
############################################################

backup_destination=$(python3 "${dcat_deploy_dir}"/backup/get_dcat_backup_destination.py "${data_catalog_path}")

if [ -n "${backup_destination}" ]
then
    if [ -z "${BRANCH_NAME}" ]
    then
        echo "Please specify dcat-deploy BRANCH_NAME to use for deploying scheduled backups"
        exit 1
    fi

    # Prepare backup job payload
    sed "${dcat_deploy_dir}"/backup/cloudbuild_backup.json \
        -e "s|__DEST_BUCKET__|${backup_destination}|" \
        -e "s|__GITHUB_SECRET_ID__|${GITHUB_SECRET_ID}|" \
        -e "s|__BRANCH_NAME__|${BRANCH_NAME}|" > cloudbuild_backup_gen.json

    echo "Scheduling backup..."

    # Check if job already exists
    echo " + Check if job ${PROJECT_ID}-run-backup exists..."
    job_exists=$(gcloud scheduler jobs list --project="${PROJECT_ID}" | grep "${PROJECT_ID}"-run-backup)

    # Delete job if it already exists
    if [[ -n "${job_exists}" ]]
    then
        echo " + Deleting existing job ${PROJECT_ID}-run-backup..."
        gcloud scheduler jobs delete "${PROJECT_ID}"-run-backup --quiet
    fi

    # Random minute for scheduler
    minute=$(shuf -i 1-30 -n 1)

    # (Re)create job
    echo " + Creating job ${PROJECT_ID}-run-backup..."
    gcloud scheduler jobs create http "${PROJECT_ID}"-run-backup \
        --schedule="${minute} 4 * * *" \
        --uri="https://cloudbuild.googleapis.com/v1/projects/${PROJECT_ID}/builds" \
        --message-body-from-file=cloudbuild_backup_gen.json \
        --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
        --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform
fi

if [ $? -ne 0 ]
then
    echo "ERROR scheduling backup job"
    exit 1
fi

############################################################
# Schedule topic history jobs
############################################################

topics_and_periods=$(python3 "${dcat_deploy_dir}"/catalog/scripts/generate_topic_list.py "${data_catalog_path}")

if [ -n "${topics_and_periods}" ]
then

    if [ -z "${SERVICE_ACCOUNT}" ]
    then
        echo "ERROR service account should be specified when project contains a topic"
        exit 1
    fi

    "${dcat_deploy_dir}"/history/create_history_function.sh "${PROJECT_ID}" "${BRANCH_NAME}" "${SERVICE_ACCOUNT}"
    "${dcat_deploy_dir}"/history/create_history_scheduler.sh "${PROJECT_ID}" "${topics_and_periods}"
fi

if [ $? -ne 0 ]
then
    echo "ERROR creating pub/sub topic history function and job"
    exit 1
fi
