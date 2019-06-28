#!/bin/bash

data_catalog_file=${1}
PROJECT_ID=${2}
keyring_region=${3}
keyring=${4}
key=${5}
b64_encrypted_github_token=${6}

if [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <data_catalog_file> <project_id> <keyring_region> <keyring> <key> <b64_encrypted_github_token>"
    exit 1
fi

basedir=$(dirname $0)

if [ -n "${key}" ]
then
    echo "decrypting github access token using key ${key}@${keyring}"
    echo "encrypted token: ${b64_encrypted_github_token}"
    github_token=$(echo ${b64_encrypted_github_token} | base64 -d - | gcloud kms decrypt \
        --key=${key} \
        --keyring=${keyring} \
        --location=${keyring_region} \
        --ciphertext-file=- \
        --plaintext-file=- \
        --project=${PROJECT_ID})
fi

git clone --branch=0.24.0 https://github.com/josegonzalez/python-github-backup.git
export PYTHONPATH=python-github-backup
mkdir output

for repo in $(python3 ${basedir}/list_github_repos.py ${data_catalog_file} | head -n1)
do
   echo "Backup ${repo} from ${PROJECT_ID}"
   organization=$(echo $repo | cut -d/ -f1)
   reponame=$(echo $repo | cut -d/ -f2)
   python-github-backup/bin/github-backup --token=${github_token} --all --organization --repository=${reponame%.*} --output-directory=output --prefer-ssh ${organization}
done
