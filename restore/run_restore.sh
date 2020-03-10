#!/bin/bash
# shellcheck disable=SC2181

helpFunction()
{
    echo ""
    echo "Usage: $0 -b [BACKUP_BUCKET] -p [PROJECT_ID] -t [TARGET_PROJECT] -d [DATA_CATALOG] -f [FORMATS] -d"
    echo -e "-b Bucket name that contains the backup(s)"
    echo -e "-p Project name to restore the backup(s) from"
    echo -e "-t Project name to restore the backup(s) to"
    echo -e "-d Path to data_catalog.json"
    exit 1
}

while getopts "s:t:d:f" opt
do
    case "$opt" in
        b ) BACKUP_BUCKET="$OPTARG" ;;
        p ) PROJECT_ID="$OPTARG" ;;
        t ) TARGET_PROJECT="$OPTARG" ;;
        d ) DATA_CATALOG="$OPTARG" ;;
        f ) FORMATS="$OPTARG" ;;
        ? ) helpFunction ;;
    esac
done

if [ -z "${BACKUP_BUCKET}" ] || [ -z "${PROJECT_ID}" ] || [ -z "${TARGET_PROJECT}" ] || [ -z "${DATA_CATALOG}" ] || [ -z "${FORMATS}" ]
then
    echo "Some or all of the parameters are empty";
    helpFunction
fi

# Begin script in case all parameters are correct
echo "${BACKUP_BUCKET}"
echo "${PROJECT_ID}"
echo "${TARGET_PROJECT}"
echo "${DATA_CATALOG}"
echo "${FORMATS}"

[[ -n "${PROJECT}" ]] || error_exit "Missing required PROJECT"
[[ -n "${SERVICE}" ]] || error_exit "Missing required SERVICE"
[[ -n "${CONFIG_ID}" ]] || error_exit "Missing required CONFIG_ID"

# Check if there is already a data_catalog.json deployed
deployments=$(gcloud deployment-manager deployments list \
  --project="${TARGET_PROJECT}" \
  --simple-list)

if [[ ! "${deployments}" == *${TARGET_PROJECT}-dcat-deploy* ]]
then
    echo "Target project ${TARGET_PROJECT} does not contain a valid deployment, deploy data_catalog.json first!"
    exit 1
fi

# List contents of backup bucket


basedir=$(dirname "$0")
result=0

#########################################################################
# Restore blob-storage
#########################################################################

if [[ ${FORMATS} == *blob-storage* ]]
then
    echo "Restoring blob-storage...";

    "${basedir}"/storage/restore_storage_buckets.sh "${DATA_CATALOG}" "${PROJECT_ID}"

    if [ $? -ne 0 ]
    then
        echo "ERROR restoring blob-storage"
        result=1
    fi
fi

#########################################################################
# Restore mysql
#########################################################################

if [[ ${FORMATS} == *mysql-db* ]]
then
    echo "Restoring mysql...";
fi

#########################################################################
# Restore cloudsql
#########################################################################

if [[ ${FORMATS} == *cloudsql-db* ]]
then
    echo "Restoring postgresql...";
fi

#########################################################################
# Restore datastore
#########################################################################

if [[ ${FORMATS} == *datastore* ]]
then
    echo "Restoring datastore...";
fi

#########################################################################
# Restore firestore
#########################################################################

if [[ ${FORMATS} == *firestore* ]]
then
    echo "Restoring firestore...";
fi
