#!/bin/bash

# This scripts deploys the data management (datasets, backup, clean up, ...) of the specified data catalog to GCP

data_catalog_path=${1}
PROJECT_ID=${2}

dcat_deploy_dir=$(dirname $0)

if [ -z "${PROJECT_ID}" ]
then
    echo "Usage: $0 <data_catalog_path> <PROJECT_ID>"
    exit 1
fi

# Deploy datasets
${dcat_deploy_dir}/catalog/scripts/deploy_data_catalog.sh ${PROJECT_ID}-dcat-deploy ${data_catalog_path} ${PROJECT_ID}

