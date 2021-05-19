#!/bin/bash
# shellcheck disable=SC1091,SC2181

DEPLOYMENT_NAME=${1}
DATA_CATALOG=${2}
PROJECT_ID=${3}
BRANCH_NAME=${4}

SCHEMAS_FOLDER=${5:-""}
SCHEMAS_CONFIG=${6:-""}
RUN_MODE=${7:-"deploy"}
CONFIG_PROJECT=${8:-""}

function get_identity_token() {
    AUDIENCE="https://europe-west1-${CONFIG_PROJECT}.cloudfunctions.net/${CONFIG_PROJECT}-kvstore"
    SERVICE_ACCOUNT="kvstore@${CONFIG_PROJECT}.iam.gserviceaccount.com"

    token=$(curl \
        --silent \
        --request POST \
        --header "content-type: application/json" \
        --header "Authorization: Bearer $(gcloud auth print-access-token)" \
        --data "{\"audience\": \"${AUDIENCE}\" }" \
        "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${SERVICE_ACCOUNT}:generateIdToken")

    identity_token=$(echo "${token}" | python3 -c "import sys, json; j=json.loads(sys.stdin.read()); print(j['token'])")
}

function get_key_value() {

    # If no identity token is available, get that first
    if [ -z "${identity_token}" ]; then
        get_identity_token
    fi

    key="${1}"
    
    value=$(curl \
    --silent \
    --request GET \
    --header "Content-Type: application/json" \
    --header "Authorization: bearer ${identity_token}" \
    https://europe-west1-"${CONFIG_PROJECT}".cloudfunctions.net/"${CONFIG_PROJECT}"-kvstore/kv/"${key}")

    echo "${value}"
}

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
gcp_cloudtasks_scripts="$(mktemp -d)/cloudtasks.txt"

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
# Setup virtual env
############################################################
if [ -z "$(which pip3)" ]
then
    pip install virtualenv==16.7.9
else
    pip3 install virtualenv
fi
virtualenv -p python3 venv
. venv/bin/activate
pip install -r "${basedir}"/requirements.txt
deactivate

############################################################
# Generate datastore indexes
############################################################
. venv/bin/activate
python3 "${basedir}"/generate_datastore_indexes.py "${DATA_CATALOG}" > "${gcp_datastore_indexes}"
deactivate

############################################################
# Generate Cloud Tasks deployment scripts
############################################################

. venv/bin/activate
python3 "${basedir}"/generate_cloud_tasks_scripts.py "${DATA_CATALOG}" > "${gcp_cloudtasks_scripts}"
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
    python3 "${basedir}"/deploy_firestore_indexes.py "${DATA_CATALOG}"
    deactivate

    # Deploy Cloud Tasks Queues
    while read -r script; do
      if ! eval "gcloud tasks queues create ${script}" | eval "gcloud tasks queues update ${script}"
      then
          echo "ERROR deploying Cloud Tasks queue: \"${script}\""
          exit 1
      fi
    done < "${gcp_cloudtasks_scripts}"

    gsutil cp "${gcp_catalog}" gs://"${PROJECT_ID}"-dcat-deployed-stg/data_catalog.json
    
    publish_project=""
    publish_topic=""

    if  [ -n "${CONFIG_PROJECT}" ]
    then
        get_identity_token

        publish_project=$(get_key_value "publishDataCatalog/project")
        echo "${publish_project}"
        publish_topic=$(get_key_value "publishDataCatalog/topic")
        echo "${publish_topic}"

        publish_project=$(curl \
        --silent \
        --request GET \
        --header "Content-Type: application/json" \
        --header "Authorization: bearer ${identity_token}" \
        https://europe-west1-"${CONFIG_PROJECT}".cloudfunctions.net/"${CONFIG_PROJECT}"-kvstore/kv/publishDataCatalog/project)

        echo "${publish_project}"

        publish_topic=$(curl \
        --silent \
        --request GET \
        --header "Content-Type: application/json" \
        --header "Authorization: bearer ${identity_token}" \
        https://europe-west1-"${CONFIG_PROJECT}".cloudfunctions.net/"${CONFIG_PROJECT}"-kvstore/kv/publishDataCatalog/topic)
    fi

    # Post the data catalog to the data catalogs topic
    . venv/bin/activate &&
    if ! python3 "${basedir}"/publish_dcat_to_topic.py -d "${gcp_catalog}" -p "${PROJECT_ID}" -t "${publish_topic}" -n "${publish_project}"
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

        if  [ -n "${CONFIG_PROJECT}" ]
        then
            get_identity_token

            topic_project_id=$(curl \
            --silent \
            --request GET \
            --header "Content-Type: application/json" \
            --header "Authorization: bearer ${identity_token}" \
            https://europe-west1-"${CONFIG_PROJECT}".cloudfunctions.net/"${CONFIG_PROJECT}"-kvstore/kv/publishJSONSchema/project)

            topic_name=$(curl \
            --silent \
            --request GET \
            --header "Content-Type: application/json" \
            --header "Authorization: bearer ${identity_token}" \
            https://europe-west1-"${CONFIG_PROJECT}".cloudfunctions.net/"${CONFIG_PROJECT}"-kvstore/kv/publishJSONSchema/topic)
        else    
            topic_project_id=$(sed -n "s/\s*topic_project_id.*:\s*\(.*\)$/\1/p" "${SCHEMAS_CONFIG}" | head -n1)
            topic_name=$(sed -n "s/\s*topic_name.*:\s*\(.*\)$/\1/p" "${SCHEMAS_CONFIG}" | head -n1)
        fi

        # Run the script that publishes the schema
        . venv/bin/activate
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
