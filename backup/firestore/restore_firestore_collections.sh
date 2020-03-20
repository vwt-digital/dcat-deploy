#!/bin/bash
# shellcheck disable=SC2181

BACKUP_BUCKET=${1}
PROJECT_ID=${2}

if [ -z "${BACKUP_BUCKET}" ] || [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <backup_bucket> <project_id>"
    exit 1
fi

result=0

# Suppress error message when no backup is found
metadata_files=$(gsutil ls -r "gs://${BACKUP_BUCKET}/backup/firestore" 2> /dev/null | grep overall_export_metadata || true )

if [[ -n "${metadata_files}" ]]
then
    latest=$(echo "${metadata_files}" | tac | head -1)
    echo -e " + Restoring firestore backup from ${latest%/*}"
    gcloud firestore import "${latest%/*}" --project="${PROJECT_ID}"
fi

if [ $? -ne 0 ]
then
    echo "ERROR restoring firestore backup from ${latest}"
    result=1
fi

exit $result
