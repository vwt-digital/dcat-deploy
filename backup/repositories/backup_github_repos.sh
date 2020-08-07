#!/bin/bash

data_catalog_file=${1}
PROJECT_ID=${2}
dest_bucket=${3}
github_secret_id=${4}

if [ -z "${dest_bucket}" ]
then
    echo "Usage: $0 <data_catalog_file> <project_id> <dest_bucket> <github_secret_id>"
    exit 1
fi

basedir=$(dirname "$0")

if [ -n "${github_secret_id}" ]
then
    github_token=$(gcloud secrets versions access latest --secret="${github_secret_id}")
fi

git clone --branch=0.33.1 https://github.com/josegonzalez/python-github-backup.git
export PYTHONPATH=python-github-backup
mkdir output

result=0

for repo in $(python3 "${basedir}"/list_github_repos.py "${data_catalog_file}")
do
   echo "Create backup of ${repo} from ${PROJECT_ID}"
   organization=$(echo "${repo}" | cut -d/ -f1)
   reponamegit=$(echo "${repo}" | cut -d/ -f2)
   reponame=${reponamegit%.*}

   if ! python-github-backup/bin/github-backup \
        --token="${github_token}" \
        --all \
        --private \
        --fork \
        --organization \
        --throttle-limit=5000 \
        --throttle-pause=0.6 \
        --repository="${reponame}" \
        --output-directory=output "${organization}";
   then
       echo "ERROR during backup of ${repo} from ${PROJECT_ID}"
       result=1
   fi

   destpath="gs://${dest_bucket}/backup/github/${reponame}.tgz"
   echo "Copy backup of ${repo} to ${destpath}"
   cd output/repositories && \
   tar -zcvf "${reponame}".tgz "${reponame}" && \
   gsutil cp "${reponame}".tgz "${destpath}"


   # shellcheck disable=SC2181
   if [ $? -ne 0 ]
   then
       echo "ERROR during copy backup of ${repo} to ${destpath}"
       result=1
   fi

   rm -rf "${reponame}" "${reponame}".tgz
   cd ../.. || exit 1
done

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during repo backup"
fi

exit ${result}
