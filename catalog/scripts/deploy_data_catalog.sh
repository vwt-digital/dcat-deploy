#!/bin/bash
# shellcheck disable=SC1091,SC2181

DEPLOYMENT_NAME=${1}
DATA_CATALOG=${2}
PROJECT_ID=${3}
BRANCH_NAME=${4}

SCHEMAS_FOLDER=""
if [ -n "${5}" ]
then
    SCHEMAS_FOLDER=${5}
fi

SCHEMAS_CONFIG=""
if [ -n "${6}" ]
then
    SCHEMAS_CONFIG=${6}
fi

RUN_MODE=${7:-"deploy"}

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

if [ -n "${SCHEMAS_FOLDER}" ]; then
    get_abs_filename() {
        echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
    }
    SCHEMAS_FOLDER_ABS_PATH=$(get_abs_filename "${SCHEMAS_FOLDER}")
    python3 "${basedir}"/data_catalog_sanity_check.py -d "${DATA_CATALOG}" -b "${BRANCH_NAME}" -r "${roles}" -s "${services}" -sf "${SCHEMAS_FOLDER_ABS_PATH}"
else
    python3 "${basedir}"/data_catalog_sanity_check.py -d "${DATA_CATALOG}" -b "${BRANCH_NAME}" -r "${roles}" -s "${services}"
fi

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

python3 "${basedir}"/prepare_data_catalog.py -c "${DATA_CATALOG}" -p "${PROJECT_ID}" > "${gcp_catalog}"

{
    echo "catalog = \\"
    sed -e "s/:\s*true/: True/g" -e "s/:\s*false/: False/g" "${gcp_catalog}"
    cat "${basedir}"/deploy_data_catalog.py
} > "${gcp_template}"

############################################################
# Generate datastore indexes
############################################################

if [ -z "$(which pip3)" ]
then
    pip install virtualenv==16.7.9
else
    pip3 install virtualenv
fi
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

    # Deploy FireStore indexes
    . venv/bin/activate
    pip install google-cloud-firestore==1.9.0
    python3 "${basedir}"/deploy_firestore_indexes.py "${DATA_CATALOG}"
    deactivate

    gsutil cp "${gcp_catalog}" gs://"${PROJECT_ID}"-dcat-deployed-stg/data_catalog.json

    # Post the data catalog to the data catalogs topic
    . venv/bin/activate &&
    pip install google-cloud-pubsub==1.7.0
    pip install gobits==0.0.7
    if ! python3 "${basedir}"/publish_dcat_to_topic.py -d "${gcp_catalog}" -p "${PROJECT_ID}"
    then
        echo "ERROR publishing data_catalog."
        exit 1
    fi &&
    deactivate &&

    # Check if the schemas folder is given as a parameter
    if [ -n "${SCHEMAS_FOLDER}" ]; then
        # Post the schema to the schemas topic
        # Also post schema to the schemas storage
        # Only if the data catalog has schemas
        . venv/bin/activate
        pip install google-cloud-pubsub==1.7.0
        pip install gobits==0.0.7
        pip install google-cloud-storage==1.31.0
        pip install jsonschema==3.2.0

        get_abs_filename() {
            echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
        }
        echo "Schemas folder found"
        SCHEMAS_FOLDER_ABS_PATH=$(get_abs_filename "${SCHEMAS_FOLDER}")
        SCHEMAS_ARR=()
        # For every schema in the schemas folder
        for f in "${SCHEMAS_FOLDER_ABS_PATH}"/*.json;
        do
            SCHEMAS_ARR+=("$f")
        done
        if [ -z "${SCHEMAS_CONFIG}" ]
        then
            echo "Schema config variable cannot be found."
            exit 1
        fi
        if [ "${BRANCH_NAME}" == "develop" ]
        then
            topic_project_id=$(sed -n "s/\s*topic_project_id_develop.*:\s*\(.*\)$/\1/p" "${SCHEMAS_CONFIG}" | head -n1)
            topic_name=$(sed -n "s/\s*topic_name_develop.*:\s*\(.*\)$/\1/p" "${SCHEMAS_CONFIG}" | head -n1)
        elif [ "${BRANCH_NAME}" == "master" ]
        then
            topic_project_id=$(sed -n "s/\s*topic_project_id_production.*:\s*\(.*\)$/\1/p" "${SCHEMAS_CONFIG}" | head -n1)
            topic_name=$(sed -n "s/\s*topic_name_production.*:\s*\(.*\)$/\1/p" "${SCHEMAS_CONFIG}" | head -n1)
        fi

        # Run the script that publishes the schema
        if ! python3 "${basedir}"/publish_schema_to_topic.py -d "${gcp_catalog}" -tpi "${topic_project_id}" -tn "${topic_name}" -s "${SCHEMAS_ARR[@]}"
        then
            echo "ERROR publishing schema."
            exit 1
        fi
        deactivate
    fi

else
    cat "${gcp_template}" "${basedir}"/test.py > "${gcp_template}".test.py
    python3 "${gcp_template}".test.py

    echo
    echo GCP DataStore index.yaml:
    cat "${gcp_datastore_indexes}"
fi
