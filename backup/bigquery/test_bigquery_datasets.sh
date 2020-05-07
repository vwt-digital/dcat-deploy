#!/bin/bash
# shellcheck disable=SC2181

DATASET=${1}
PROJECT_ID=${2}


if [ -z "${DATASET}" ] || [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <dataset> <project_id>"
    exit 1
fi

result=0

tables=$(bq ls "${PROJECT_ID}:${DATASET}" | awk '{print $1}' | tail -n +3)

if [ -z "$tables" ]
then
    echo "ERROR ${DATASET} contains no tables"
    result=1
fi

exit $result
