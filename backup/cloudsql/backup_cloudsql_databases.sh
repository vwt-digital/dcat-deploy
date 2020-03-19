#!/bin/bash
# shellcheck disable=SC2181

data_catalog_file=${1}
PROJECT_ID=${2}
dest_bucket=${3}

if [ -z "${dest_bucket}" ]
then
    echo "Usage: $0 <data_catalog_file> <project_id> <dest_bucket>"
    exit 1
fi

basedir=$(dirname "$0")
result=0

for pair in $(python3 "${basedir}"/list_cloudsql_databases.py "${data_catalog_file}")
do
    instance=$(echo "${pair}" | cut -d'|' -f 1)
    database=$(echo "${pair}" | cut -d'|' -f 2)

    echo "Create backup of database ${database} in project ${PROJECT_ID}"
    gcloud sql export sql "${instance}" "gs://${dest_bucket}/backup/cloudsql/${instance}/${database}/sqldumpfile.gz" \
      --database="${database}" \
      --project="${PROJECT_ID}"

    if [ $? -ne 0 ]
    then
        echo "Checking for pending operations for backup of ${database} in project ${PROJECT_ID}..."
        PENDING_OPERATIONS=$(gcloud sql operations list \
          --instance="${instance}" \
          --filter='status!=DONE' \
          --format='value(name)')
        if [ -n "${PENDING_OPERATIONS}" ]
        then
            echo "Found pending operation ${PENDING_OPERATIONS}"
            # Waiting for pending operations for a specified amount of seconds
            gcloud sql operations wait "${PENDING_OPERATIONS}" --timeout=1800
            if [ $? -ne 0 ]
            then
                echo "ERROR waiting for pending backup operations"
                result=1
            fi
        else
            echo "ERROR creating backup of ${database} in project ${PROJECT_ID}"
            result=1
        fi
    fi
done

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during backup of ${PROJECT_ID}"
fi

exit $result
