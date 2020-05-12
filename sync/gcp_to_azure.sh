#!/bin/bash
# shellcheck disable=SC2181

function error_exit() {
  # ${BASH_SOURCE[1]} is the file name of the caller.
  echo "${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${1:-Unknown Error.} (exit ${2:-1})" 1>&2
  exit "${2:-1}"
}

while getopts :p:i:u:e: arg; do
  case ${arg} in
    p) PROJECT_ID="${OPTARG}";;
    i) IAM_ACCOUNT="${OPTARG}";;
    u) SAS_URL="${OPTARG}";;
    e) ENDS_WITH="${OPTARG}";;
    \?) error_exit "Unrecognized argument -${OPTARG}";;
  esac
done

[[ -n "${PROJECT_ID}" ]] || error_exit "Missing required PROJECT_ID"
[[ -n "${IAM_ACCOUNT}" ]] || error_exit "Missing required IAM_ACCOUNT"
[[ -n "${SAS_URL}" ]] || error_exit "Missing required SAS_URL"
[[ -n "${ENDS_WITH}" ]] || error_exit "Missing required ENDS_WITH"

basedir=$(dirname "$0")
result=0

echo "Installing rclone..."
apt-get update -y
apt-get install unzip -y
curl https://rclone.org/install.sh | bash

echo "Creating credentials for ${SERVICE_ACCOUNT}..."
credentials_file="${basedir}/credentials.json"
gcloud iam service-accounts keys create "${credentials_file}" \
  --iam-account "${IAM_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com}"

echo "Creating rclone config..."
config_file="${basedir}/rclone.conf"
cat << EOF > "${config_file}"
[azure]
type = azureblob
sas_url = ${SAS_URL}

[gcp]
type = google cloud storage
service_account_file = ${credentials_file}
EOF

for bucket in $(gsutil ls -p "${PROJECT_ID}" | grep "${ENDS_WITH}")
do
    echo " + Syncing ${bucket} to Azure"
    bucket_name=$(echo "${bucket}" | cut -d '/' -f 3)
    rclone sync "gcp:${bucket_name}" "azure:${bucket_name}" --config="${config_file}" -P

    if [ $? -ne 0 ]
    then
        echo "ERROR syncing ${bucket} to Azure"
        result=1
    fi
done

exit $result
