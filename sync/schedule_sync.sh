#!/bin/bash
# shellcheck disable=SC2181

function error_exit() {
  # ${BASH_SOURCE[1]} is the file name of the caller.
  echo "${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${1:-Unknown Error.} (exit ${2:-1})" 1>&2
  exit "${2:-1}"
}

while getopts :z:p:b:i:s:c: arg; do
  case ${arg} in
    z) ZONE="${OPTARG}";;
    p) PROJECT_ID="${OPTARG}";;
    b) BRANCH_NAME="${OPTARG}";;
    i) IAM_ACCOUNT="${OPTARG}";;
    s) SECRET_NAME="${OPTARG}";;
    c) SCHEDULE="${OPTARG}";;
    \?) error_exit "Unrecognized argument -${OPTARG}";;
  esac
done

[[ -n "${ZONE}" ]] || error_exit "Missing required ZONE"
[[ -n "${PROJECT_ID}" ]] || error_exit "Missing required PROJECT_ID"
[[ -n "${BRANCH_NAME}" ]] || error_exit "Missing required BRANCH_NAME"
[[ -n "${IAM_ACCOUNT}" ]] || error_exit "Missing required IAM_ACCOUNT"
[[ -n "${SECRET_NAME}" ]] || error_exit "Missing required SECRET_NAME"
[[ -n "${SCHEDULE}" ]] || error_exit "Missing required SCHEDULE"

basedir=$(dirname "$0")
result=0

echo "Generating cloudbuild.json..."
sed "${basedir}"/cloudbuild.json \
  -e "s|__BRANCH_NAME__|${BRANCH_NAME}|" \
  -e "s|__ZONE__|${ZONE}|" \
  -e "s|__SECRET_NAME__|${SECRET_NAME}|" \
  -e "s|__IAM_ACCOUNT__|${IAM_ACCOUNT}|" > cloudbuild_gen.json

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
    --schedule="${SCHEDULE}" \
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
