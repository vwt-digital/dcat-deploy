#!/bin/bash

zone=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/zone" -H "Metadata-Flavor: Google")
project_id=$(curl "http://metadata.google.internal/computeMetadata/v1/project/project-id" -H "Metadata-Flavor: Google")
branch_name=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/branch-name" -H "Metadata-Flavor: Google")
iam_account=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/iam-account" -H "Metadata-Flavor: Google")
hostname=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/hostname" -H "Metadata-Flavor: Google")
secret_name=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/secret-name" -H "Metadata-Flavor: Google")
ends_with=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/ends-with" -H "Metadata-Flavor: Google")

basedir=$(dirname "$0")

apt-get update && apt-get install git -y
git clone --branch="${branch_name}" https://github.com/vwt-digital/dcat-deploy.git "${basedir}/dcat-deploy"

sas_url=$(gcloud secrets versions access latest --secret="${secret_name}")

"${basedir}"/dcat-deploy/sync/gcp_to_azure.sh \
  -p "${project_id}" \
  -i "${iam_account}" \
  -u "${sas_url}" \
  -e "${ends_with}"

instance_name=$(echo "${hostname}" | cut -d '.' -f 1)
gcloud compute instances delete "${instance_name}" --zone="${zone}" --quiet
