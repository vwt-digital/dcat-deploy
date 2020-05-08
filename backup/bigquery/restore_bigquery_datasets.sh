#!/bin/bash
# shellcheck disable=SC2181

BACKUP_BUCKET=${1}
PROJECT_ID=${2}
DATASET=${3}

if [ -z "${BACKUP_BUCKET}" ] || [ -z "${PROJECT_ID}" ] || [ -z "${DATASET}" ]
then
    echo "Usage: $0 <backup_bucket> <project_id> <dataset>"
    exit 1
fi

result=0

for backup in $(gsutil ls "gs://${BACKUP_BUCKET}/backup/bigquery/${DATASET}/")
do

    # Only restore the latest partition from backup
    backups=$(gsutil ls -r "${backup}" 2> /dev/null | grep extract.avro || true)
    latest=$(echo "${backups}" | tac | head -1)
    table=$(echo "${latest}" | cut -d '/' -f 7)

    if [ -n "${latest}" ]
    then
       echo -e " + Restoring bigquery backup from ${latest}"
       bq load \
        --source_format=AVRO \
        "${PROJECT_ID}:${DATASET}.${table}" \
        "$latest"
    fi

    if [ $? -ne 0 ]
    then
        echo "ERROR restoring backup from ${latest}"
        result=1
    fi

done

exit $result
