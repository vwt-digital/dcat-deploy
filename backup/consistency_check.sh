#!/bin/bash
# shellcheck disable=SC2181,SC1091

DATA_CATALOG=${1}
PROJECT_ID=${2}

if [ -z "${DATA_CATALOG}" ] || [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <data_catalog> <project_id>"
    exit 1
fi

basedir=$(dirname "$0")
result=0

#########################################################################
# Consistency check blob-storage
#########################################################################

echo "Performing consistency check on storage buckets..."

for bucket in $(python3 "${basedir}"/storage/list_storage_buckets.py "${DATA_CATALOG}")
do
    python3 "${basedir}"/storage/test_storage_buckets.py "${bucket}"
done

if [ $? -ne 0 ]
then
    echo "ERROR storage buckets not consistent"
    result=1
fi

#########################################################################
# Consistency check cloudsql
#########################################################################

echo "Performing consistency check on cloudsql databases..."

if [[ -n $(python3 "${basedir}"/cloudsql/list_cloudsql_databases.py "${DATA_CATALOG}") ]]
then
    python3 "${basedir}"/cloudsql/test_cloudsql_databases.py "${PROJECT_ID}"
fi

if [ $? -ne 0 ]
then
    echo "ERROR cloudsql databases not consistent"
    result=1
fi

#########################################################################
# Consistency check firestore
#########################################################################

echo "Performing consistency check on firestore collections..."

if [[ -n $(python3 "${basedir}"/firestore/list_firestores.py "${DATA_CATALOG}") ]]
then
    python3 "${basedir}"/firestore/test_firestore_collections.py
fi

if [ $? -ne 0 ]
then
    echo "ERROR firestore collections not consistent"
    result=1
fi

#########################################################################
# Consistency check datastore
#########################################################################

echo "Performing consistency check on datastore kinds..."

if [[ -n $(python3 "${basedir}"/datastore/list_datastores.py "${DATA_CATALOG}") ]]
then
    python3 "${basedir}"/datastore/test_datastore_kinds.py
fi

if [ $? -ne 0 ]
then
    echo "ERROR datastore kinds not consistent"
    result=1
fi

exit $result
