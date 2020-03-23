#!/bin/bash
# shellcheck disable=SC2181

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

if [ $? -ne 0 ]
then
    echo "ERROR creating backup of datastore to ${destpath}"
    result=1
fi

exit $result
