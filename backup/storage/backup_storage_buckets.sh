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

for bucket in $(python3 "${basedir}"/list_storage_buckets.py "${data_catalog_file}")
do

    if [[ ! "${bucket}" == "*-backup-stg" ]]
    then

        echo "Create backup of ${bucket} from ${PROJECT_ID}"
        gsutil -m rsync -d -r "gs://${bucket}" "gs://${dest_bucket}/backup/storage/${bucket}"

        if [ $? -ne 0 ]
        then
           echo "ERROR creating backup of ${bucket} from ${PROJECT_ID}"
           result=1
        fi

    fi

done

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during backup of ${PROJECT_ID}"
fi

exit $result
