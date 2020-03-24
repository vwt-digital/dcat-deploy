#!/bin/bash
# shellcheck disable=SC2181

DATA_CATALOG=${1}
BACKUP_BUCKET=${2}
PROJECT_ID=${3}

if [ -z "${DATA_CATALOG}" ] || [ -z "${BACKUP_BUCKET}" ] || [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <data_catalog> <backup_bucket> <project_id>"
    exit 1
fi

basedir=$(dirname "$0")
result=0

#########################################################################
# Consistency check blob-storage
#########################################################################
