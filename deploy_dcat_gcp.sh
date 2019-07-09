#!/bin/bash

# This scripts deploys the data management (datasets, backup, clean up, ...) of the specified data catalog to GCP

data_catalog_path=${1}
PROJECT_ID=${2}

if [ -n "${3}" ]
then
    BRANCH_NAME=${3}
else
    BRANCH_NAME="master"
fi

backup_bucket=${4}
encrypted_github_token=${5}

dcat_deploy_dir=$(dirname $0)

if [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <data_catalog_path> <PROJECT_ID> <BRANCH_NAME> [backup_bucket] [encrypted_github_token]"
    exit 1
fi

############################################################
# Deploy datasets
############################################################

# Deploy resources using deployment manager
${dcat_deploy_dir}/catalog/scripts/deploy_data_catalog.sh ${PROJECT_ID}-dcat-deploy ${data_catalog_path} ${PROJECT_ID}

if [ $? -ne 0 ]
then
    echo "Error deploying data catalog"
    exit 1
fi

# Update pushConfig of topic subscriptions (currently not supported by Deployment Manager)
python ${dcat_deploy_dir}/catalog/scripts/update_subscriptions.py -d ${data_catalog_path} -p ${PROJECT_ID}

if [ $? -ne 0 ]
then
    echo "Error updating pubsub subscription pushConfig"
    exit 1
fi


############################################################
# Schedule backup job
############################################################

if [ -n "${backup_bucket}" ]
then
    # Prepare backup job payload
    sed ${dcat_deploy_dir}/backup/cloudbuild_backup.json \
        -e "s/__DEST_BUCKET__/${backup_bucket}/" \
        -e "s/__ENCRYPTED_GITHUB_TOKEN__/${encrypted_github_token}/" \
        -e "s/__DCAT_DEPLOY_BRANCH_NAME__/${BRANCH_NAME}/"

    echo "Scheduling backup..."
    # Check if job already exists
    echo " + Check if job ${PROJECT_ID}-run-backup exists..."
    gcloud scheduler jobs describe ${PROJECT_ID}-run-backup
    job_exists=$?

    # Delete job if it already exists
    if [ ${job_exists} -eq 0 ]
    then
        echo " + Deleting existing job ${PROJECT_ID}-run-backup..."
        gcloud scheduler jobs delete ${PROJECT_ID}-run-backup
    fi

    # (Re)create job
    echo " + Creating job ${PROJECT_ID}-run-backup..."
    gcloud scheduler jobs create ${PROJECT_ID}-run-backup http \
        --schedule='0 5 * * *' \
        --uri=https://cloudbuild.googleapis.com/v1/projects/${PROJECT_ID}/builds \
        --message-body-from-file=       \
        --oauth-service-account-email=${PROJECT_ID}@appspot.gserviceaccount.com \
        --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform
fi

