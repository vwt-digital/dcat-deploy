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

############################################################
# Deploy datasets
############################################################

# Deploy resources using deployment manager
${dcat_deploy_dir}/catalog/scripts/deploy_data_catalog.sh ${PROJECT_ID}-dcat-deploy ${data_catalog_path} ${PROJECT_ID}

if [ $? -ne 0 ]
then
    echo "Error deploying data catalog"
    exit 1
fi

# Update pushConfig of topic subscriptions (currently not supported by Deployment Manager)
python ${dcat_deploy_dir}/catalog/scripts/update_subscriptions.py -d ${data_catalog_path} -p ${PROJECT_ID}

if [ $? -ne 0 ]
then
    echo "Error updating pubsub subscription pushConfig"
    exit 1
fi
