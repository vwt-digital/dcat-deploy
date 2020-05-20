#!/bin/bash
# shellcheck disable=SC2181

function error_exit() {
  # ${BASH_SOURCE[1]} is the file name of the caller.
  echo "${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${1:-Unknown Error.} (exit ${2:-1})" 1>&2
  exit "${2:-1}"
}

while getopts :p:u: arg; do
  case ${arg} in
    p) PROJECT_ID="${OPTARG}";;
    u) SAS_URL="${OPTARG}";;
    \?) error_exit "Unrecognized argument -${OPTARG}";;
  esac
done

[[ -n "${PROJECT_ID}" ]] || error_exit "Missing required PROJECT_ID"
[[ -n "${SAS_URL}" ]] || error_exit "Missing required SAS_URL"

basedir=$(dirname "$0")
result=0

echo "Installing rclone..."
apt-get update -y
apt-get install unzip jq -y
curl https://rclone.org/install.sh | bash

echo "Creating rclone config..."
config_file="${basedir}/rclone.conf"
cat << EOF > "${config_file}"
[azure]
type = azureblob
sas_url = ${SAS_URL}

[gcp]
type = google cloud storage
# credential file of default sa is used
EOF

for bucket in $(gsutil ls -p "${PROJECT_ID}")
do

    echo "Checking gcp bucket ${bucket}..."
    mirror=$(gsutil label get "${bucket}" | jq -er '.mirror')

    if [ $? -eq 0 ]
    then

        echo " + Syncing ${bucket} to Azure"
        bucket_name=$(echo "${bucket}" | cut -d '/' -f 3)
        rclone sync "gcp:${bucket_name}" "azure:${mirror}" --config="${config_file}" -P

        if [ $? -ne 0 ]
        then
            echo "ERROR syncing ${bucket} to Azure"
            result=1
        fi

    fi

done

exit $result
