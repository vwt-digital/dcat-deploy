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

metadata_file=$(gsutil ls -r "gs://${BACKUP_BUCKET}/backup/firestore" | grep overall_export_metadata | tail -r | head -1)

echo -e "Restoring firestore backup from ${metadata_file}"
gcloud firestore import "${metadata_file}" --project="${PROJECT_ID}"

if [ $? -ne 0 ]
then
   echo "ERROR restoring firestore backup from ${metadata_file}"
   result=1
fi

exit $result
