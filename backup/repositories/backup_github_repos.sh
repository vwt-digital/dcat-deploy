#!/bin/bash

data_catalog_file=${1}
PROJECT_ID=${2}
dest_bucket=${3}
keyring_region=${4}
keyring=${5}
key=${6}
b64_encrypted_github_token=${7}

if [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <data_catalog_file> <project_id> <keyring_region> <keyring> <key> <b64_encrypted_github_token>"
    exit 1
fi

basedir=$(dirname $0)

if [ -n "${key}" ]
then
    echo "decrypting github access token using key ${key}@${keyring}"
    github_token=$(echo ${b64_encrypted_github_token} | base64 -d - | gcloud kms decrypt \
        --key=${key} \
        --keyring=${keyring} \
        --location=${keyring_region} \
        --ciphertext-file=- \
        --plaintext-file=- \
        --project=${PROJECT_ID})

    if [ $? -ne 0 ]
    then
        echo "Error decoding github access token"
        exit 1
    fi
fi

git clone --branch=0.24.0 https://github.com/josegonzalez/python-github-backup.git
export PYTHONPATH=python-github-backup
mkdir output

for repo in $(python3 ${basedir}/list_github_repos.py ${data_catalog_file})
do
   echo "Create backup of ${repo} from ${PROJECT_ID}"
   organization=$(echo $repo | cut -d/ -f1)
   reponamegit=$(echo $repo | cut -d/ -f2)
   reponame=${reponamegit%.*}
   python-github-backup/bin/github-backup --token=${github_token} --all --private --organization --repository=${reponame} --output-directory=output ${organization}

   destpath="gs://${dest_bucket}/github/$(date +%Y/%m/%d)/${reponame}.tgz"
   echo "Copy backup of ${repo} to ${destpath}"
   cd output/repositories
   tar -zcvf ${reponame}.tgz ${reponame}
   gsutil cp ${reponame}.tgz ${destpath}
   rm -rf ${reponame} ${reponame}.tgz
   cd ../..
done
