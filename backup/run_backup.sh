#!/bin/bash

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

basedir=$(dirname $0)

#########################################################################
# Backup repositories
#########################################################################

${basedir}/repositories/backup_github_repos.sh ${data_catalog_file} ${PROJECT_ID} ${dest_bucket} ${keyring_region} ${keyring} ${key} ${b64_encrypted_github_token}

if [ $? -ne 0 ]
then
    echo "ERROR backing up source code repositories"
    exit 1
fi

#########################################################################
# Backup storage buckets
#########################################################################

${basedir}/storage/backup_storage_buckets.sh ${data_catalog_file} ${PROJECT_ID} ${dest_bucket}

if [ $? -ne 0 ]
then
    echo "ERROR backing up storage buckets"
    exit 1
fi
