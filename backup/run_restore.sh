#!/bin/bash
# shellcheck disable=SC2181

BACKUP_BUCKET=${1}
DATA_CATALOG=${2}
PROJECT_ID=${4}

if [ -z "${BACKUP_BUCKET}" ] || [ -z "${DATA_CATALOG}" ] || [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <backup_bucket> <source_bucket> <dest_bucket> <project_id>"
    exit 1
fi

basedir=$(dirname "$0")
result=0

#########################################################################
# Restore blob-storage
#########################################################################

echo "Restoring blob-storage..."

for bucket in $(python3 "${basedir}"/storage/list_storage_buckets.py "${DATA_CATALOG}")
do
    source_bucket=$(python3 "${basedir}"/get_dcat_backup_source.py "${bucket}")

    "${basedir}"/cloudsql/restore_cloudsql_databases.sh "${BACKUP_BUCKET}" \
      "${source_bucket}" \
      "${bucket}" \
      "${PROJECT_ID}"
done

if [ $? -ne 0 ]
then
    echo "ERROR restoring blob-storage"
    result=1
fi

#########################################################################
# Restore cloudsql
#########################################################################

echo "Restoring cloudsql..."

for pair in $(python3 "${basedir}"/cloudsql/list_cloudsql_databases.py "${DATA_CATALOG}")
do
    destination_instance=$(echo "${pair}" | cut -d'|' -f 1)
    destination_database=$(echo "${pair}" | cut -d'|' -f 2)

    source_instance=$(python3 "${basedir}"/get_dcat_backup_source.py "${destination_instance}")
    source_database=$(python3 "${basedir}"/get_dcat_backup_source.py "${destination_database}")

    "${basedir}"/cloudsql/restore_cloudsql_databases.sh "${BACKUP_BUCKET}" \
      "${source_instance}" \
      "${source_database}" \
      "${destination_instance}" \
      "${destination_database}" \
      "${PROJECT_ID}"
done

if [ $? -ne 0 ]
then
    echo "ERROR restoring cloudsql"
    result=1
fi

#########################################################################
# Restore datastore
#########################################################################

echo "Restoring datastore..."

if [[ -n $(python3 "${basedir}"/datastore/list_datastores.py "${DATA_CATALOG}") ]]
then
    "${basedir}"/datastore/restore_datastore_kinds.sh "${BACKUP_BUCKET}" "${PROJECT_ID}"
fi

if [ $? -ne 0 ]
then
    echo "ERROR restoring datastore"
    result=1
fi

#########################################################################
# Restore firestore
#########################################################################

echo "Restoring firestore..."

if [[ -n $(python3 "${basedir}"/firestore/list_firestores.py "${DATA_CATALOG}") ]]
then
    "${basedir}"/firestore/restore_firestore_collections.sh "${BACKUP_BUCKET}" "${PROJECT_ID}"
fi

if [ $? -ne 0 ]
then
    echo "ERROR restoring firestore"
    result=1
fi

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during restore"
fi
