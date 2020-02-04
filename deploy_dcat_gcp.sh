#!/bin/bash

# This scripts deploys the data management (datasets, backup, clean up, ...) of the specified data catalog to GCP

data_catalog_path=${1}
PROJECT_ID=${2}
BRANCH_NAME=${3}
encrypted_github_token=${4}

dcat_deploy_dir=$(dirname $0)

if [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <data_catalog_path> <PROJECT_ID> <BRANCH_NAME> [encrypted_github_token]"
    exit 1
fi

############################################################
# Create and configure github repos (only when a github token is provided)
############################################################

if [ -n "${encrypted_github_token}" ]
then
    echo ${encrypted_github_token} | base64 -d - | \
    gcloud kms decrypt \
      --ciphertext-file=- \
      --plaintext-file=${dcat_deploy_dir}/catalog/repos/github_access_token.key \
      --location=europe-west1 \
      --keyring=github \
      --key=github-access-token

    ${dcat_deploy_dir}/catalog/repos/create_github_repos.sh ${data_catalog_path} ${dcat_deploy_dir}/catalog/repos/github_access_token.key
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

backup_destination=$(python3 ${dcat_deploy_dir}/backup/get_dcat_backup_destination.py ${data_catalog_path})

if [ -n "${backup_destination}" ]
then
    if [ -z "${BRANCH_NAME}" ]
    then
        echo "Please specify dcat-deploy BRANCH_NAME to use for deploying scheduled backups"
        exit 1
    fi

    # Prepare backup job payload
    sed ${dcat_deploy_dir}/backup/cloudbuild_backup.json \
        -e "s|__DEST_BUCKET__|${backup_destination}|" \
        -e "s|__ENCRYPTED_GITHUB_TOKEN__|${encrypted_github_token}|" \
        -e "s|__DCAT_DEPLOY_BRANCH_NAME__|${BRANCH_NAME}|" > cloudbuild_backup_gen.json

    echo "Scheduling backup..."
    # Check if job already exists
    echo " + Check if job ${PROJECT_ID}-run-backup exists..."
    gcloud scheduler jobs describe ${PROJECT_ID}-run-backup
    job_exists=$?

    # Delete job if it already exists
    if [ ${job_exists} -eq 0 ]
    then
        echo " + Deleting existing job ${PROJECT_ID}-run-backup..."
        gcloud scheduler jobs delete --quiet ${PROJECT_ID}-run-backup
    fi

    # (Re)create job
    echo " + Creating job ${PROJECT_ID}-run-backup..."
    gcloud scheduler jobs create http ${PROJECT_ID}-run-backup \
        --schedule='0 5 * * *' \
        --uri=https://cloudbuild.googleapis.com/v1/projects/${PROJECT_ID}/builds \
        --message-body-from-file=cloudbuild_backup_gen.json \
        --oauth-service-account-email=${PROJECT_ID}@appspot.gserviceaccount.com \
        --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform
fi

############################################################
# Schedule topic history jobs
############################################################

echo " + Deleting existing jobs..."
for job in $(gcloud scheduler jobs list  --project=${PROJECT_ID} | grep history-job | awk '{ print $1 }')
do
    echo " + Deleting existing job $job..."
    gcloud scheduler jobs delete "$job" --project=${PROJECT_ID} --quiet
done

pairs=$(python3 ${dcat_deploy_dir}/catalog/scripts/generate_topic_list.py ${data_catalog_path})

if [ ! -z "$pairs" ]
then
    echo " + Cloning pubsub-backup repo..."
    git clone --branch=${BRANCH_NAME} https://github.com/vwt-digital/pubsub-backup.git
    (cd pubsub-backup/functions/pubsub-backup && gcloud functions deploy ${PROJECT_ID}-history-func \
      --entry-point=handler \
      --runtime=python37 \
      --trigger-http \
      --project=${PROJECT_ID} \
      --region=europe-west1 \
      --memory=2048MB \
      --timeout=540s \
      --set-env-vars=PROJECT_ID=${PROJECT_ID},MAX_RETRIES="3",MAX_MESSAGES="1000",TOTAL_MESSAGES="250000")

    echo " + Setting permissions for ${PROJECT_ID}-history-func..."
    cat << EOF > backup_func_permissions.json
    { "bindings": [ { "members": [ "serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" ], "role": "roles/cloudfunctions.invoker" } ] }
    EOF

    gcloud beta functions set-iam-policy ${PROJECT_ID}-history-func \
      --region=europe-west1 \
      --project=${PROJECT_ID} \
      backup_func_permissions.json
fi

for pair in $pairs
do
    topic=$(echo ${pair} | cut -d'|' -f 1)
    period=$(echo ${pair} | cut -d'|' -f 2)

    if [[ $period =~ T+.(M$|S$) ]]
    then
      cron="0 * * * *"
    else
      cron="0 00,06,12,18 * * *"
    fi

    echo " + Creating job ${topic}-history-job..."
    gcloud scheduler jobs create http ${topic}-history-job \
      --schedule="${cron}" \
      --uri=https://europe-west1-${PROJECT_ID}.cloudfunctions.net/${PROJECT_ID}-history-func/ \
      --http-method=POST \
      --oidc-service-account-email=${PROJECT_ID}@appspot.gserviceaccount.com \
      --oidc-token-audience=https://europe-west1-${PROJECT_ID}.cloudfunctions.net/${PROJECT_ID}-history-func \
      --message-body="${topic}-history-sub"
done
