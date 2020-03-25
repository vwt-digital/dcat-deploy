#!/bin/sh
# shellcheck disable=SC1091,SC2181

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

basedir=$(dirname "$0")

gcp_template=$(mktemp "${deployment_name}"-XXXXX.py)
gcp_catalog=$(mktemp "${deployment_name}"-catalog-XXXXX.json)
gcp_datastore_indexes="$(mktemp -d)/index.yaml"

if ! python3 "${basedir}"/data_catalog_sanity_check.py "${data_catalog}"
then
    echo "Sanity check failed"
    exit 1
fi

echo "Sanity chec passed"

python3 "${basedir}"/prepare_data_catalog.py "${data_catalog}" "${project_id}" > "${gcp_catalog}"

{
    echo "catalog = \\"
    sed -e "s/:\s*true/: True/g" -e "s/:\s*false/: False/g" "${gcp_catalog}"
    cat "${basedir}"/deploy_data_catalog.py
} > "${gcp_template}"

pip install virtualenv==16.7.9
virtualenv -p python3 venv
. venv/bin/activate
pip install pyyaml
python3 "${basedir}"/generate_datastore_indexes.py "${data_catalog}" > "${gcp_datastore_indexes}"
deactivate

if [ "${runmode}" = "deploy" ]
then
    # Check if deployment exists
    gcloud deployment-manager deployments describe "${deployment_name}" --project="${project_id}" >/dev/null 2>&1
    result=$?

    if [ "${result}" -ne 0 ]
    then
        # Create if deployment does not yet exist
        gcloud deployment-manager deployments create "${deployment_name}" --template="${gcp_template}" --project="${project_id}"
    else
        # Update if deployment exists already
        gcloud deployment-manager deployments update "${deployment_name}" --template="${gcp_template}" --project="${project_id}"
    fi

    if [ $? -ne 0 ]
    then
        echo "Error deploying data catalog."
        exit 1
    fi

    # Deploy DataStore indexes
    if [ -s "${gcp_datastore_indexes}" ]
    then
        # Create new DataStore indexes
        if ! gcloud datastore indexes create "${gcp_datastore_indexes}" --quiet --project="${project_id}"
        then
            echo "Error deploying datastore indexes."
            exit 1
        fi

        # Cleanup old DataStore indexes
        if ! gcloud datastore indexes cleanup "${gcp_datastore_indexes}" --quiet --project="${project_id}"
        then
            echo "Error cleaning up datastore indexes."
            exit 1
        fi
    fi

    gsutil cp "${gcp_catalog}" gs://"${project_id}"-dcat-deployed-stg/data_catalog.json

    # Post the data catalog to the data catalogs topic
    . venv/bin/activate
    pip install google-cloud-pubsub==1.2.0
    if ! python3 "${basedir}"/publish_dcat_to_topic.py -d "${gcp_catalog}" -p "${project_id}"
    then
        echo "Error publishing data_catalog."
        exit 1
    fi
    deactivate

else
    cat "${gcp_template}" "${basedir}"/test.py > "${gcp_template}".test.py
    python3 "${gcp_template}".test.py

    echo
    echo GCP DataStore index.yaml:
    cat "${gcp_datastore_indexes}"
fi
