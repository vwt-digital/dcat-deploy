#!/bin/bash
# shellcheck disable=SC2181

BACKUP_BUCKET=${1}
SOURCE_INSTANCE=${2}
SOURCE_DATABASE=${3}
DEST_INSTANCE=${4}
DEST_DATABASE=${5}
PROJECT_ID=${6}

if [ -z "${BACKUP_BUCKET}" ] || [ -z "${SOURCE_INSTANCE}" ] ||
   [ -z "${SOURCE_DATABASE}" ] || [ -z "${DEST_INSTANCE}" ] ||
   [ -z "${DEST_DATABASE}" ] || [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <backup_bucket> <source_instance> <source_database> <dest_instance> <dest_database> <project_id>"
    exit 1
fi

result=0

echo -e "Restoring backup from:"
echo -e "\t Bucket: gs://${BACKUP_BUCKET}"
echo -e "\t Instance: ${SOURCE_INSTANCE}"
echo -e "\t Database: ${SOURCE_DATABASE}"
echo -e "To database in project ${PROJECT_ID}:"
echo -e "\t Instance: ${DEST_INSTANCE}"
echo -e "\t Database: ${DEST_DATABASE}"

sa=$(gcloud sql instances describe "${DEST_INSTANCE}" \
  --format="value(serviceAccountEmailAddress)" \
  --project="${PROJECT_ID}")

echo -e "Make sure ${sa} has the following permissions:"
echo -e "\t Resource: ${BACKUP_BUCKET}"
echo -e "\t Role: roles/storage.legacyBucketReader"
echo -e "\t Role: roles/storage.legacyObjectReader"

file="gs://${BACKUP_BUCKET}/backup/cloudsql/${SOURCE_INSTANCE}/${SOURCE_DATABASE}/sqldumpfile.gz"

gcloud sql import sql "${DEST_INSTANCE}" "${file}" \
  --database="${DEST_DATABASE}" \
  --project="${PROJECT_ID}" \
  --async \
  --quiet

if [ $? -ne 0 ]
then
    echo "ERROR restoring backup from ${file}"
    result=1
fi

exit $result
