#!/bin/bash
# shellcheck disable=SC2181

BACKUP_BUCKET=${1}
SOURCE_DATABASE=${2}
DEST_INSTANCE=${3}
DEST_DATABASE=${4}
PROJECT_ID=${5}

if [ -z "${BACKUP_BUCKET}" ] || [ -z "${SOURCE_DATABASE}" ] || [ -z "${DEST_INSTANCE}" ] || [ -z "${DEST_DATABASE}" ] || [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <backup_bucket> <source_database> <dest_instance> <dest_database> <project_id>"
    exit 1
fi

result=0

echo -e "Restoring backup from:"
echo -e "\t gs://${BACKUP_BUCKET}/backup/cloudsql/${SOURCE_DATABASE}"
echo -e "To database in project ${PROJECT_ID}:"
echo -e "\t Instance: ${DEST_INSTANCE}"
echo -e "\t Database: ${DEST_DATABASE}"

sa=$(gcloud sql instances describe test-database \
  --project=vwt-d-gew1-backup-restore-chk | grep serviceAccountEmailAddress: | cut -d ' ' -f 2)

# Set temporary role for backup restore
gsutil iam ch serviceAccount:"${sa}":roles/storage.legacyBucketWriter gs://${BACKUP_BUCKET}
gsutil iam ch serviceAccount:"${sa}":roles/storage.objectViewer gs://${BACKUP_BUCKET}

gcloud sql import sql ${DEST_INSTANCE} gs://${BACKUP_BUCKET}/backup/cloudsql/${SOURCE_DATABASE}/ \
  --database=${DEST_DATABASE}

# Remove temporary role for backup restore
gsutil iam ch -d serviceAccount:"${sa}" gs://${BACKUP_BUCKET}

if [ $? -ne 0 ]
then
   echo "ERROR restoring backup from gs://${BACKUP_BUCKET}/backup/clouddsql/${SOURCE_DATABASE}"
   result=1
fi

exit $result
