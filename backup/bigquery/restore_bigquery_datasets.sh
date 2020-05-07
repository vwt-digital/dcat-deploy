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

for table in $(gsutil ls "gs://${BACKUP_BUCKET}/backup/bigquery/${DATASET}/")
do
    backups=$(gsutil ls -r "${table}" 2> /dev/null | grep extract.avro || true)

    # Only restore the latest partition from backup
    latest=$(echo "$backups" | tac | head -1)

    if [ -n "${latest}" ]
    then
       echo -e " + Restoring bigquery backup from ${latest}"
       bq load \
        --source_format=AVRO \
        "${DATASET}.${table}" \
        "$latest"
    fi

    if [ $? -ne 0 ]
    then
        echo "ERROR restoring backup from ${latest}"
        result=1
    fi

done

exit $result
