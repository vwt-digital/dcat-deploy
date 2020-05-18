#!/bin/bash
# shellcheck disable=SC2181

PROJECT_ID=${1}
DEST_BUCKET=${2}
LOCAL_BUCKET=${3}
DATASET=${4}

if [ -z "${PROJECT_ID}" ] || [ -z "${DEST_BUCKET}" ] || [ -z "${LOCAL_BUCKET}" ] || [ -z "${DATASET}" ]
then
    echo "Usage: $0 <project_id> <dest_bucket> <local_bucket> <dataset>"
    exit 1
fi

basedir=$(dirname "$0")
result=0

echo "Creating backup of bigquery dataset ${DATASET}..."
python3 "${basedir}"/backup_bigquery_datasets.py -p "${PROJECT_ID}" -d "${DATASET}" -b "${LOCAL_BUCKET}"

echo " + Syncing project local bigquery backup"
gsutil -m rsync -d -r "gs://${LOCAL_BUCKET}/backup/bigquery" "gs://${DEST_BUCKET}/backup/bigquery"

echo " + Cleaning project local bigquery backup"
gsutil -m rm "gs://${LOCAL_BUCKET}/backup/bigquery/**"

if [ $? -ne 0 ]
then
    result=1
fi

exit $result
