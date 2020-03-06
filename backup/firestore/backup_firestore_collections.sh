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
    echo "Create backup of collection ${collection} from ${PROJECT_ID}"
    destpath="gs://${dest_bucket}/backup/firestore/$(date '+%Y/%m/%d/%H')/${collection}"
    gcloud firestore export ${destpath} --collection-ids="${collection}"

    if [ $? -ne 0 ]
    then
        echo "ERROR creating backup of ${collection} to ${destpath}"
        result=1
    fi
done

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during firestore backup"
fi

exit $result
