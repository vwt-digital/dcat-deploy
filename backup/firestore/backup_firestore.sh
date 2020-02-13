#!/bin/bash

PROJECT_ID=${1}
dest_bucket=${2}

if [ -z "${dest_bucket}" ]
then
    echo "Usage: $0 <project_id> <dest_bucket>"
    exit 1
fi

basedir=$(dirname $0)
result=0

for collection in $(python3 ${basedir}/list_firestore_collections.py)
do
    echo "Create backup of ${collection} from ${PROJECT_ID}"
    gcloud firestore export gs://${dest_bucket}/backup/firestore --collection-ids=${collection}

    if [ $? -ne 0 ]
    then
        echo "ERROR creating backup of ${bucket} from ${PROJECT_ID}"
        result=1
    fi
done

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during backup of ${PROJECT_ID}"
fi

exit $result
