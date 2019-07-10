#!/bin/sh

if [ -z "${3}" ]
then
    echo "Usage: $0 <deployment_name> <data_catalog_file> <project_id> [test]"
    exit 1
fi

if [ "${4}" = "test" ]
then
    runmode="test"
else
    runmode="deploy"
fi

deployment_name="${1}"
data_catalog="${2}"
project_id="${3}"

basedir=$(dirname $0)

gcp_template=$(mktemp ${deployment_name}-XXXXX.py)
gcp_catalog=$(mktemp ${deployment_name}-catalog-XXXXX.json)

python3 ${basedir}/add_dcat_stg.py ${data_catalog} ${project_id} > ${gcp_catalog}

{
    echo "catalog = \\"
    cat ${gcp_catalog}
    cat ${basedir}/deploy_data_catalog.py
} > ${gcp_template}

if [ "${runmode}" = "deploy" ]
then
    # Check if deployment exists
    gcloud deployment-manager deployments describe ${deployment_name} --project=${project_id} >/dev/null 2>&1
    result=$?

    if [ ${result} -ne 0 ]
    then
        # Create if deployment does not yet exist
        gcloud deployment-manager deployments create ${deployment_name} --template=${gcp_template} --project=${project_id}
    else
        # Update if deployment exists already
        gcloud deployment-manager deployments update ${deployment_name} --template=${gcp_template} --project=${project_id}
    fi

    if [ $? -ne 0 ]
    then
        echo "Error deploying data catalog."
        exit 1
    fi

    gsutil cp ${gcp_catalog} gs://${project_id}-dcat-deployed-stg/data_catalog.json
else
    cat ${gcp_template} ${basedir}/test.py > ${gcp_template}.test.py
    python3 ${gcp_template}.test.py
fi