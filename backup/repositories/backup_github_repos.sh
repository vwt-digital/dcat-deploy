#!/bin/bash

data_catalog_file=${1}
PROJECT_ID=${2}

if [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <data_catalog_file> <project_id>"
    exit 1
fi

basedir=$(dirname $0)

git clone --branch=0.24.0 https://github.com/josegonzalez/python-github-backup.git

for repo in $(python3 ${basedir}/list_github_repos.py ${data_catalog_file})
do
   echo "Backup ${repo} from ${PROJECT_ID}"
done
