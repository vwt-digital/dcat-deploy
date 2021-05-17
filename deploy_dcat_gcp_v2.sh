#!/usr/bin/env bash

# This scripts deploys the data management (datasets, backup, clean up, ...) of the specified data catalog to GCP

usage() {
cat << EOF
Usage: ${0} <DATA_CATALOG_PATH> <PROJECT_ID> <BRANCH_NAME> [-g GITHUB_SECRET_ID] [-s SERVICE_ACCOUNT] [-f SCHEMAS_FOLDER -c SCHEMAS_CONFIG] [-e CONFIG_PROJECT]
    DATA_CATALOG_PATH ... Path to the data catalog
    PROJECT_ID .......... Google Project ID
    BRANCH_NAME ......... Git branch
    GITHUB_SECRET_ID .... Github secret ID
    SERVICE_ACCOUNT ..... Google service account
    SCHEMAS_FOLDER ...... Path to the schemas
    SCHEMAS_CONFIG ...... Schema config
    CONFIG_PROJECT ...... Location of configuration server
EOF
}

get_identity_token() {
    AUDIENCE="https://europe-west1-${CONFIG_PROJECT}.cloudfunctions.net/${CONFIG_PROJECT}-kvstore"
    SERVICE_ACCOUNT="kvstore@${CONFIG_PROJECT}.iam.gserviceaccount.com"
    
    token=$(curl \
        --silent \
        --request POST \
        --header "content-type: application/json" \
        --header "Authorization: Bearer $(gcloud auth print-access-token)" \
        --data "{\"audience\": \"${AUDIENCE}\" }" \
        "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${SERVICE_ACCOUNT}:generateIdToken")

    identity_token=$(echo "${token}" | python3 -c "import sys, json; j=json.loads(sys.stdin.read()); print(j['token'])")
}

DATA_CATALOG_PATH=${1}
PROJECT_ID=${2}
BRANCH_NAME=${3}

shift 3

GITHUB_SECRET_ID=""
SERVICE_ACCOUNT=""
SCHEMAS_FOLDER=""
SCHEMAS_CONFIG=""
CONFIG_PROJECT=""

while getopts "s:g:f:c:e:" opt; do
    case ${opt} in
        g) GITHUB_SECRET_ID=${OPTARG} ;;
        s) SERVICE_ACCOUNT=${OPTARG} ;;
        f) SCHEMAS_FOLDER=${OPTARG} ;;
        c) SCHEMAS_CONFIG=${OPTARG} ;;
        e) CONFIG_PROJECT=${OPTARG} ;;
        [?]) usage && exit 1;
    esac
done

if [ -z "${PROJECT_ID}" ]
then
    usage && exit 1
   
fi

if  [ -z "${CONFIG_PROJECT}" ]
then
    get_identity_token
    echo "$identity_token"
fi


dcat_deploy_dir=$(dirname "$0")

############################################################
# Create and configure github repos
############################################################

if [ -n "${GITHUB_SECRET_ID}" ]
then
    "${dcat_deploy_dir}"/catalog/repos/create_github_repos.sh "${DATA_CATALOG_PATH}" "${GITHUB_SECRET_ID}"
fi

############################################################
# Deploy datasets using deployment manager
############################################################

"${dcat_deploy_dir}"/catalog/scripts/deploy_data_catalog.sh "${PROJECT_ID}"-dcat-deploy "${DATA_CATALOG_PATH}" "${PROJECT_ID}" "${BRANCH_NAME}" "${SCHEMAS_FOLDER}" "${SCHEMAS_CONFIG}" "" "${CONFIG_PROJECT}"

# shellcheck disable=SC2181
if [ $? -ne 0 ]
then
    echo "ERROR deploying data catalog"
    exit 1
fi

############################################################
# Schedule backup job
############################################################

backup_destination=$(python3 "${dcat_deploy_dir}"/backup/get_dcat_backup_destination.py "${DATA_CATALOG_PATH}")

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

# shellcheck disable=SC2181
if [ $? -ne 0 ]
then
    echo "ERROR scheduling backup job"
    exit 1
fi

############################################################
# Schedule topic history jobs
############################################################

topics_and_periods=$(python3 "${dcat_deploy_dir}"/catalog/scripts/generate_topic_list.py "${DATA_CATALOG_PATH}")

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

# shellcheck disable=SC2181
if [ $? -ne 0 ]
then
    echo "ERROR creating pub/sub topic history function and job"
    exit 1
fi

#########################################################################
# Create functions to backup repositories
#########################################################################

if [ -n "${GITHUB_SECRET_ID}" ]
then
  echo "Creating functions to backup source code repositories..."

  "${dcat_deploy_dir}"/backup/repositories/setup_backup_github_repos.sh "${DATA_CATALOG_PATH}" "${PROJECT_ID}" "${backup_destination}" "${GITHUB_SECRET_ID}"

  # shellcheck disable=SC2181
  if [ $? -ne 0 ]
  then
    echo "ERROR creating functions"
    exit 1
  fi
fi
