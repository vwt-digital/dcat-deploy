#!/bin/bash
# shellcheck disable=SC2181

DATA_CATALOG_FILE=${1}
PROJECT_ID=${1}
DEST_BUCKET=${2}


if [ -z "${DATA_CATALOG_FILE}" ] || [ -z "${PROJECT_ID}" ] || [ -z "${DEST_BUCKET}" ]
then
    echo "Usage: $0 <data_catalog_file> <project_id> <dest_bucket>"
    exit 1
fi

basedir=$(dirname "$0")
result=0

for dataset in $(python3 "${basedir}"/list_bigquery_datasets.py "${DATA_CATALOG_FILE}")
do

    python3 "${basedir}"/backup_bigquery_datasets.py -p "${PROJECT_ID}" -d "${dataset}" -b "${DEST_BUCKET}"

    if [ $? -ne 0 ]
    then
        echo "ERROR creating backup of bigquery dataset ${dataset}"
        result=1
    fi

done

exit $result
