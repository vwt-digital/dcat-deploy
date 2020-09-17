#!/bin/bash

function error_exit() {
  # ${BASH_SOURCE[1]} is the file name of the caller.
  echo "${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${1:-Unknown Error.} (exit ${2:-1})" 1>&2
  exit "${2:-1}"
}

while getopts :z:p:b:i:s: arg; do
  case ${arg} in
    z) ZONE="${OPTARG}";;
    p) PROJECT_ID="${OPTARG}";;
    b) BRANCH_NAME="${OPTARG}";;
    i) IAM_ACCOUNT="${OPTARG}";;
    s) SECRET_NAME="${OPTARG}";;
    \?) error_exit "Unrecognized argument -${OPTARG}";;
  esac
done

[[ -n "${ZONE}" ]] || error_exit "Missing required ZONE"
[[ -n "${PROJECT_ID}" ]] || error_exit "Missing required PROJECT_ID"
[[ -n "${BRANCH_NAME}" ]] || error_exit "Missing required BRANCH_NAME"
[[ -n "${IAM_ACCOUNT}" ]] || error_exit "Missing required IAM_ACCOUNT"
[[ -n "${SECRET_NAME}" ]] || error_exit "Missing required SECRET_NAME"

basedir=$(dirname "$0")

network_name="${PROJECT_ID}-sync-nw"

network_exists=$(gcloud compute networks list \
  --project "${PROJECT_ID}" \
  --filter "name:${network_name}" \
  --format "value(name)")

if [[ -z "${network_exists}" ]]
then
    echo " + Creating network ${network_name}"
    gcloud compute networks create "${network_name}" \
      --project "${PROJECT_ID}" --quiet
fi

instance_name="${PROJECT_ID}-sync-vm"

instance_exists=$(gcloud compute instances list \
  --project "${PROJECT_ID}" \
  --filter "name:${instance_name}" \
  --format "value(name)")

if [[ -n "${instance_exists}" ]]
then
    echo " + Deleting instance ${instance_name}"
    gcloud compute instances delete "${instance_name}" \
      --zone="${ZONE}" --project "${PROJECT_ID}" --quiet
fi

echo " + Creating instance ${instance_name}"
gcloud compute instances create "${instance_name}" \
  --zone "${ZONE}" \
  --project "${PROJECT_ID}" \
  --network "${network_name}" \
  --scopes cloud-platform \
  --service-account "${IAM_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --metadata "serial-port-enable=true,branch-name=${BRANCH_NAME},iam-account=${IAM_ACCOUNT},secret-name=${SECRET_NAME}" \
  --metadata-from-file startup-script="${basedir}"/startup_script.sh \
  --machine-type "g1-small" \
  --boot-disk-size "25GB" \
  --preemptible

while [[ -n $(gcloud compute instances list --project "${PROJECT_ID}" --format "value(status)" --filter "name:${instance_name}") ]]
do
    echo " + Connecting to serial port ${IAM_ACCOUNT}@${instance_name}"
    gcloud compute connect-to-serial-port "${IAM_ACCOUNT}@${instance_name}" \
      --zone "${ZONE}" \
      --project "${PROJECT_ID}"

    echo " + Sleeping for 60 seconds"
    sleep 60
done
