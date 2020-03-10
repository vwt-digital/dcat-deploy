#!/bin/bash
# shellcheck disable=SC2181

BACKUP_BUCKET=${1}
SOURCE_BUCKET=${2}
DEST_BUCKET=${3}
PROJECT_ID=${4}

if [ -z "${BACKUP_BUCKET}" ] || [ -z "${SOURCE_BUCKET}" ] || [ -z "${DEST_BUCKET}" ] || [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <backup_bucket> <source_bucket> <dest_bucket> <project_id>"
    exit 1
fi

result=0

echo -e "Restoring backup from:"
echo -e "\t gs://${BACKUP_BUCKET}/backup/storage/${SOURCE_BUCKET}"
echo -e "To bucket in project ${PROJECT_ID}:"
echo -e "\t gs://${DEST_BUCKET}"

gsutil -m cp -r "gs://${BACKUP_BUCKET}/backup/storage/${SOURCE_BUCKET}/*" "gs://${DEST_BUCKET}"

if [ $? -ne 0 ]
then
   echo "ERROR restoring backup from gs://${BACKUP_BUCKET}/backup/storage/${SOURCE_BUCKET}"
   result=1
fi

exit $result
