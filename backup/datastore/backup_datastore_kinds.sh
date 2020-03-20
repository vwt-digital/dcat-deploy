#!/bin/bash

PROJECT_ID=${1}
dest_bucket=${2}

if [ -z "${dest_bucket}" ]
then
    echo "Usage: $0 <project_id> <dest_bucket>"
    exit 1
fi

result=0

destpath="gs://${dest_bucket}/backup/datastore/$(date '+%Y/%m/%d/%H')"
gcloud datastore export "${destpath}" --project="${PROJECT_ID}"

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during datastore backup"
fi

exit $result
