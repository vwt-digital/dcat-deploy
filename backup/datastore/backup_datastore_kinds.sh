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

for kind in $(python3 ${basedir}/list_datastore_kinds.py)
do
    echo "Create backup of kind ${kind} from ${PROJECT_ID}"
    destpath="gs://${dest_bucket}/backup/datastore/$(date '+%Y/%m/%d/%H/%M')/${kind}"
    gcloud datastore export ${destpath} --kinds="${kind}"

    if [ $? -ne 0 ]
    then
        echo "ERROR creating backup of ${kind} to ${destpath}"
        result=1
    fi
done

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during datastore backup"
fi

exit $result
