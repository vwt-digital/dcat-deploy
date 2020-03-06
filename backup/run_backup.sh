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

echo "Backup source code repositories"

"${basedir}"/repositories/backup_github_repos.sh "${data_catalog_file}" "${PROJECT_ID}" "${dest_bucket}" "${keyring_region}" "${keyring}" "${key}" "${b64_encrypted_github_token}"

if [ $? -ne 0 ]
then
    echo "ERROR backing up source code repositories"
    result=1
fi

#########################################################################
# Backup storage buckets
#########################################################################

echo "Backup storage buckets"

"${basedir}"/storage/backup_storage_buckets.sh "${data_catalog_file}" "${PROJECT_ID}" "${dest_bucket}"

if [ $? -ne 0 ]
then
    echo "ERROR backing up storage buckets"
    result=1
fi

#########################################################################
# Backup cloudsql databases
#########################################################################

echo "Backup cloudsql databases"

"${basedir}"/cloudsql/backup_cloudsql_databases.sh "${data_catalog_file}" "${PROJECT_ID}" "${dest_bucket}"

if [ $? -ne 0 ]
then
    echo "ERROR backing up cloudsql databases"
    result=1
fi

#########################################################################
# Backup firestore collections
#########################################################################

echo "Backup firestore collections"

pip install virtualenv==16.7.9
virtualenv -p python3 firestore_venv
source firestore_venv/bin/activate
pip install google-cloud-firestore==1.6.0 google-api-core==1.16.0 grpcio==1.27.2
"${basedir}"/firestore/backup_firestore_collections.sh "${PROJECT_ID}" "${dest_bucket}"
deactivate

if [ $? -ne 0 ]
then
    echo "ERROR backing up firestore collections"
    result=1
fi

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during backup"
fi

#########################################################################
# Backup datastore kinds
#########################################################################

pip install virtualenv==16.7.9
virtualenv -p python3 datastore_venv
source datastore_venv/bin/activate
pip install google-cloud-datastore==1.8.0 google-api-core==1.16.0 grpcio==1.27.2
deactivate

echo "Backup datastore kinds"

source datastore_venv/bin/activate
"${basedir}"/datastore/backup_datastore_kinds.sh "${PROJECT_ID}" "${dest_bucket}"
deactivate

if [ $? -ne 0 ]
then
    echo "ERROR backing up datastore kinds"
    result=1
fi

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during backup"
fi

#########################################################################
# Auto delete datastore entities
#########################################################################

echo "Auto delete datastore entities"

source datastore_venv/bin/activate
python3 "${basedir}"/datastore/datastore_auto_delete.py "${data_catalog_file}"
deactivate

if [ $? -ne 0 ]
then
    echo "ERROR auto deletion datastore entities"
    result=1
fi

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during auto deletion of datastore entities"
fi

exit $result
