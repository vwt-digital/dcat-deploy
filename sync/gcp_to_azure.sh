#!/bin/bash
# shellcheck disable=SC2181

PROJECT_ID=${1}
SAS_URL=${2}
SERVICE_ACCOUNT=${3}

if [ -z "${SAS_URL}" ] || [ -z "${PROJECT_ID}" ] || [ -z "${SERVICE_ACCOUNT}" ]
then
    echo "Usage: $0 <sas_url> <project_id> <service_account>"
    exit 1
fi

basedir=$(dirname "$0")
result=0

echo "Installing rclone..."
apt-get update -y
apt-get install unzip -y
curl https://rclone.org/install.sh | bash

echo "Creating gcp credentials file..."
credentials_file="${basedir}/credentials.json"
gcloud iam service-accounts keys create "${credentials_file}" \
  --iam-account "${SERVICE_ACCOUNT}"

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

for bucket in $(gsutil ls -p "${PROJECT_ID}")
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
