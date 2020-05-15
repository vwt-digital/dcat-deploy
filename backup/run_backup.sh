#!/bin/bash
# shellcheck disable=SC2181,SC1091

data_catalog_file=${1}
PROJECT_ID=${2}
dest_bucket=${3}
keyring_region=${4}
keyring=${5}
key=${6}
b64_encrypted_github_token=${7}

if [ -z "${dest_bucket}" ]
then
    echo "Usage: $0 <data_catalog_file> <project_id> <dest_bucket> [<keyring_region> <keyring> <key> <b64_encrypted_github_token>]"
    exit 1
fi

basedir=$(dirname "$0")
result=0

#########################################################################
# Backup repositories
#########################################################################

echo "Backup source code repositories..."

"${basedir}"/repositories/backup_github_repos.sh "${data_catalog_file}" "${PROJECT_ID}" "${dest_bucket}" "${keyring_region}" "${keyring}" "${key}" "${b64_encrypted_github_token}"

if [ $? -ne 0 ]
then
    echo "ERROR backing up source code repositories"
    result=1
fi


#########################################################################
# Backup storage buckets
#########################################################################

echo "Backup storage buckets..."

"${basedir}"/storage/backup_storage_buckets.sh "${data_catalog_file}" "${PROJECT_ID}" "${dest_bucket}"

if [ $? -ne 0 ]
then
    echo "ERROR backing up storage buckets"
    result=1
fi

local_bucket=$(python3 "${basedir}"/storage/list_storage_buckets.py "${data_catalog_file}" | grep "${PROJECT_ID}-backup-stg")


#########################################################################
# Backup cloudsql databases
#########################################################################

databases=$(python3 "${basedir}"/cloudsql/list_cloudsql_databases.py "${data_catalog_file}")

if [ -n "${databases}" ]
then

    echo "Backup cloudsql databases..."

    for database in ${databases}
    do
        "${basedir}"/cloudsql/backup_cloudsql_databases.sh "${PROJECT_ID}" "${dest_bucket}" "${local_bucket}" "${database}"

        if [ $? -ne 0 ]
        then
            echo "ERROR backing up cloudsql database ${database}"
            result=1
        fi

    done

fi

#########################################################################
# Backup bigquery datasets
#########################################################################

datasets=$(python3 "${basedir}"/bigquery/list_bigquery_datasets.py "${data_catalog_file}")

if [ -n "${datasets}" ]
then

    echo "Backup bigquery datasets..."

    for dataset in ${datasets}
    do

        python3 "${basedir}"/bigquery/backup_bigquery_datasets.py -p "${PROJECT_ID}" -d "${dataset}" -b "${local_bucket}"

        if [ $? -ne 0 ]
        then
            echo "ERROR creating backup of bigquery dataset ${dataset}"
            result=1
        fi

    done

fi


#########################################################################
# Backup firestore collections
#########################################################################

firestores=$(python3 "${basedir}/firestore/list_firestores.py" "${data_catalog_file}")

if [ -n "${firestores}" ]
then

    echo "Backup firestore collections..."

    "${basedir}"/firestore/backup_firestore_collections.sh "${PROJECT_ID}" "${dest_bucket}" "${local_bucket}"

    if [ $? -ne 0 ]
    then
        echo "ERROR backing up firestore collections"
        result=1
    fi

fi


#########################################################################
# Backup datastore kinds
#########################################################################

datastores=$(python3 "${basedir}/datastore/list_datastores.py" "${data_catalog_file}")

if [ -n "${datastores}" ]
then

    echo "Backup datastore kinds..."

    "${basedir}"/datastore/backup_datastore_kinds.sh "${PROJECT_ID}" "${dest_bucket}" "${local_bucket}"

    if [ $? -ne 0 ]
    then
        echo "ERROR backing up datastore kinds"
        result=1
    fi

fi


#########################################################################
# Auto delete datastore entities
#########################################################################

if [ -n "${datastores}" ]
then

    echo "Auto delete datastore entities..."

    python3 "${basedir}"/datastore/datastore_auto_delete.py "${data_catalog_file}"

    if [ $? -ne 0 ]
    then
        echo "ERROR auto deletion datastore entities"
        result=1
    fi

fi

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during backup"
fi

exit $result
