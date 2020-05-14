#!/bin/bash
# shellcheck disable=SC2181

PROJECT_ID=${1}
DEST_BUCKET=${2}
LOCAL_BUCKET=${3}

if [ -z "${PROJECT_ID}" ] || [ -z "${DEST_BUCKET}" ] || [ -z "${LOCAL_BUCKET}" ]
then
    echo "Usage: $0 <project_id> <dest_bucket>"
    exit 1
fi

result=0

echo " + Creating project local firestore backup"
local_path="gs://${LOCAL_BUCKET}/backup/firestore/$(date '+%Y/%m/%d/%H')"
gcloud firestore export "${local_path}" --project="${PROJECT_ID}"

echo " + Syncing project local firestore backup"
gsutil -m rsync -d -r "gs://${LOCAL_BUCKET}/backup/firestore" "gs://${DEST_BUCKET}/backup/firestore"

if [ ${result} -ne 0 ]
then
    echo "ERROR creating backup of firestore to gs://${DEST_BUCKET}"
    result=1
fi

exit $result
