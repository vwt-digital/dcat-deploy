#!/bin/bash
# shellcheck disable=SC2181

PROJECT_ID=${1}
DEST_BUCKET=${2}
LOCAL_BUCKET=${3}
DATABASE=${4}

if [ -z "${PROJECT_ID}" ] || [ -z "${DEST_BUCKET}" ] || [ -z "${LOCAL_BUCKET}" ] || [ -z "${DATABASE}" ]
then
    echo "Usage: $0 <project_id> <dest_bucket> <local_bucket> <database>"
    exit 1
fi

result=0

instance=$(echo "${DATABASE}" | cut -d'|' -f 1)
db_name=$(echo "${DATABASE}" | cut -d'|' -f 2)

echo "Creating backup of database ${db_name} in project ${PROJECT_ID}..."
gcloud sql export sql "${instance}" "gs://${LOCAL_BUCKET}/backup/cloudsql/${instance}/${db_name}/sqldumpfile.gz" \
  --database="${db_name}" \
  --project="${PROJECT_ID}" \
  --async

while [[ -n $(gcloud sql operations list --instance="${instance}" --filter='status!=DONE' --format='value(name)' --limit=1 --project="${PROJECT_ID}") ]]
do
    echo " + Waiting for pending operation cloudsql backup ${instance}"
    echo " + Sleeping for 60 seconds"
    sleep 60
done

echo " + Syncing project local cloudsql backup"
gsutil -m rsync -d -r "gs://${LOCAL_BUCKET}/backup/cloudsql" "gs://${DEST_BUCKET}/backup/cloudsql"

echo " + Cleaning project local cloudsql backup"
gsutil rm "gs://${LOCAL_BUCKET}/backup/cloudsql/**"

if [ $? -ne 0 ]
then
    result=1
fi

exit $result
