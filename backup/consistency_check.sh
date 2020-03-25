#!/bin/bash
# shellcheck disable=SC2181,SC1091

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

pip install virtualenv==16.7.9
virtualenv -p python3 datastore_venv
source storage_venv/bin/activate
pip install google-cloud-storage==1.26.0 \
  google-cloud-monitoring==0.34.0 \
  google-cloud-firestore==1.6.2 \
  google-cloud-datastore==1.8.0 \
  google-api-core==1.16.0 \
  grpcio==1.27.2

#########################################################################
# Consistency check blob-storage
#########################################################################

echo "Performing consistency check on storage buckets..."

python3 "${basedir}"/storage/test_storage_buckets.py

if [ $? -ne 0 ]
then
    echo "ERROR storage buckets not consistent"
    result=1
fi

#########################################################################
# Consistency check cloudsql
#########################################################################

echo "Performing consistency check on cloudsql databases..."

size=$(python3 "${basedir}"/cloudsql/test_cloudsql_databases.py "${PROJECT_ID}" "cloudsql.googleapis.com/database/disk/bytes_used")
echo "${size} bytes"

if [ $? -ne 0 ]
then
    echo "ERROR clousql databases not consistent"
    result=1
fi

#########################################################################
# Consistency check firestore
#########################################################################

echo "Performing consistency check on firestore collections..."

python3 "${basedir}"/firestore/test_firestore_collections.py

if [ $? -ne 0 ]
then
    echo "ERROR firestore collections not consistent"
    result=1
fi

#########################################################################
# Consistency check datastore
#########################################################################

echo "Performing consistency check on datastore kinds..."

python3 "${basedir}"/datastore/test_datastore_kinds.py

if [ $? -ne 0 ]
then
    echo "ERROR datastore kinds not consistent"
    result=1
fi

exit $result