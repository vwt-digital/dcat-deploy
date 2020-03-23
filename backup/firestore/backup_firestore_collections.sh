#!/bin/bash
# shellcheck disable=SC2181

PROJECT_ID=${1}
dest_bucket=${2}

if [ -z "${dest_bucket}" ]
then
    echo "Usage: $0 <project_id> <dest_bucket>"
    exit 1
fi

result=0

date_suffix=$(date '+%Y/%m/%d/%H')

localpath="gs://${PROJECT_ID}-firestore-ephemeral-backup-stg/backup/firestore/${date_suffix}"
gcloud firestore export "${localpath}" --project="${PROJECT_ID}"

destpath="gs://${dest_bucket}/backup/firestore/${date_suffix}"
gsutil -m mv "${localpath}" "${destpath}"

if [ ${result} -ne 0 ]
then
    echo "ERROR creating backup of firestore to ${destpath}"
    result=1
fi

exit $result
