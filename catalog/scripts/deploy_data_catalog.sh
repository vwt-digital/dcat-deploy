#!/bin/bash
# shellcheck disable=SC1091,SC2181

DEPLOYMENT_NAME=${1}
DATA_CATALOG=${2}
PROJECT_ID=${3}
BRANCH_NAME=${4}
RUN_MODE=${5:-"deploy"}


function error_exit() {
  # ${BASH_SOURCE[1]} is the file name of the caller.
  echo "${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${1:-Unknown Error.} (exit ${2:-1})" 1>&2
  exit "${2:-1}"
}

[[ -n "${DEPLOYMENT_NAME}" ]] || error_exit "Missing required DEPLOYMENT_NAME"
[[ -n "${DATA_CATALOG}" ]] || error_exit "Missing required DATA_CATALOG"
[[ -n "${PROJECT_ID}" ]] || error_exit "Missing required PROJECT_ID"
[[ -n "${BRANCH_NAME}" ]] || error_exit "Missing required BRANCH_NAME"

basedir=$(dirname "$0")

gcp_template=$(mktemp "${DEPLOYMENT_NAME}"-XXXXX.py)
gcp_catalog=$(mktemp "${DEPLOYMENT_NAME}"-catalog-XXXXX.json)
gcp_datastore_indexes="$(mktemp -d)/index.yaml"

services=$(gcloud services list --enabled --format="value(config.name)" --quiet --project="${PROJECT_ID}")
roles=$(gcloud projects get-iam-policy "${PROJECT_ID}" \
          --format="value(bindings.role)" \
          --flatten="bindings[].members" \
          --filter="bindings.members:group*")


############################################################
# Perform sanity check
############################################################

python3 "${basedir}"/data_catalog_sanity_check.py "${DATA_CATALOG}" "${BRANCH_NAME}" "${roles}" "${services}"
result=$?

if [ "${result}" -ne 0 ]; then
    echo "ERROR: Sanity check failed!"
    exit 1
else
    echo "Sanity check passed!"
fi


############################################################
# Prepare data catalog
############################################################

DELEGATED_SA_CONFIG_FILE=./config/${PROJECT_ID}/config.delegated_sa.yaml
if [ -f "$DELEGATED_SA_CONFIG_FILE" ]; then
    delegated_sa=$(sed -n "s/\s*delegated_sa.*:\s*\(.*\)$/\1/p" ./config/"${PROJECT_ID}"/config.delegated_sa.yaml | head -n1)
    python3 "${basedir}"/prepare_data_catalog.py -c "${DATA_CATALOG}" -p "${PROJECT_ID}" -dsa "${delegated_sa}" > "${gcp_catalog}"
else
    python3 "${basedir}"/prepare_data_catalog.py -c "${DATA_CATALOG}" -p "${PROJECT_ID}" > "${gcp_catalog}"
fi

{
    echo "catalog = \\"
    sed -e "s/:\s*true/: True/g" -e "s/:\s*false/: False/g" "${gcp_catalog}"
    cat "${basedir}"/deploy_data_catalog.py
} > "${gcp_template}"

############################################################
# Generate datastore indexes
############################################################

pip install virtualenv==16.7.9
virtualenv -p python3 venv
. venv/bin/activate
pip install pyyaml
python3 "${basedir}"/generate_datastore_indexes.py "${DATA_CATALOG}" > "${gcp_datastore_indexes}"
deactivate

############################################################
# Deploy data catalog
############################################################

if [ "${RUN_MODE}" = "deploy" ]; then

    # Check if deployment exists
    gcloud deployment-manager deployments describe "${DEPLOYMENT_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1
    result=$?

    if [ "${result}" -ne 0 ]
    then
        # Create if deployment does not yet exist
        gcloud deployment-manager deployments create "${DEPLOYMENT_NAME}" --template="${gcp_template}" --project="${PROJECT_ID}"
    else
        # Update if deployment exists already
        gcloud deployment-manager deployments update "${DEPLOYMENT_NAME}" --template="${gcp_template}" --project="${PROJECT_ID}"
    fi

    if [ $? -ne 0 ]
    then
        echo "ERROR deploying data catalog."
        exit 1
    fi

    # Deploy DataStore indexes
    if [ -s "${gcp_datastore_indexes}" ]
    then
        # Create new DataStore indexes
        if ! gcloud datastore indexes create "${gcp_datastore_indexes}" --quiet --project="${PROJECT_ID}"
        then
            echo "ERROR deploying datastore indexes."
            exit 1
        fi

        # Cleanup old DataStore indexes
        if ! gcloud datastore indexes cleanup "${gcp_datastore_indexes}" --quiet --project="${PROJECT_ID}"
        then
            echo "ERROR cleaning up datastore indexes."
            exit 1
        fi
    fi

    gsutil cp "${gcp_catalog}" gs://"${PROJECT_ID}"-dcat-deployed-stg/data_catalog.json

    # Post the data catalog to the data catalogs topic
    . venv/bin/activate &&
    pip install google-cloud-pubsub==1.2.0
    pip install gobits==0.0.7
    if ! python3 "${basedir}"/publish_dcat_to_topic.py -d "${gcp_catalog}" -p "${PROJECT_ID}"
    then
        echo "ERROR publishing data_catalog."
        exit 1
    fi &&
    deactivate &&

    # Post the schema to the schemas topic
    # Also post schema to the schemas storage
    # Only if the data catalog has schemas
    . venv/bin/activate
    pip install google-cloud-pubsub==1.2.0
    pip install gobits==0.0.7
    pip install google-cloud-storage==1.31.0
    pip install jsonschema==3.2.0

    get_abs_filename() {
        echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
    }
    SCHEMAS_FOLDER="schemas"
    # Check if there is a folder called "schemas"
    if [ -d "${SCHEMAS_FOLDER}" ]; then
        echo "Schemas folder found"
        SCHEMAS_FOLDER_ABS_PATH=$(get_abs_filename "${SCHEMAS_FOLDER}")
        schemas_list=""
        for f in "${SCHEMAS_FOLDER_ABS_PATH}"/*.json;
        do
            if [ "${schemas_list}" == "" ]; then
                schemas_list="$f"
            else
                schemas_list="${schemas_list},$f"
            fi
        done
        # For every schema in the schemas folder
        for f in "${SCHEMAS_FOLDER_ABS_PATH}"/*.json;
        do
            # Run the script that publishes the schema
            topic_project_id=$(sed -n "s/\s*topic_project_id.*:\s*\(.*\)$/\1/p" ./config/"${PROJECT_ID}"/config.schemastopic.yaml | head -n1)
            topic_name=$(sed -n "s/\s*topic_name.*:\s*\(.*\)$/\1/p" ./config/"${PROJECT_ID}"/config.schemastopic.yaml | head -n1)
            bucket_name=$(sed -n "s/\s*bucket_name.*:\s*\(.*\)$/\1/p" ./config/"${PROJECT_ID}"/config.schemastopic.yaml | head -n1)
            if ! python3 "${basedir}"/publish_schema_to_topic.py -d "${gcp_catalog}" -s "$f" -sf "${SCHEMAS_FOLDER_ABS_PATH}" -tpi "${topic_project_id}" -tn "${topic_name}" -b "${bucket_name}" -as "${schemas_list}"
            then
                echo "ERROR publishing schema."
                exit 1
            fi
        done
    fi
    deactivate

else
    cat "${gcp_template}" "${basedir}"/test.py > "${gcp_template}".test.py
    python3 "${gcp_template}".test.py

    echo
    echo GCP DataStore index.yaml:
    cat "${gcp_datastore_indexes}"
fi
