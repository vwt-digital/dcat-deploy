#!/bin/bash

data_catalog_file=${1}
PROJECT_ID=${2}
dest_bucket=${3}

if [ -z "${dest_bucket}" ]
then
    echo "Usage: $0 <data_catalog_file> <project_id> <dest_bucket>"
    exit 1
fi

basedir=$(dirname $0)
result=0

for pair in $(python3 ${basedir}/list_cloudsql_databases.py ${data_catalog_file})
do
   instance=$(echo ${pair} | cut -d'|' -f 1)
   database=$(echo ${pair} | cut -d'|' -f 2)

   echo "Create backup of ${database} from ${PROJECT_ID}"
   gcloud sql export sql ${instance} gs://${dest_bucket}/backup/cloudsql/sqldumpfile_${database}.gz \
    --database=${database} \
    --project=${PROJECT_ID} \
    --async

   if [ $? -ne 0 ]
   then
       echo "ERROR creating backup of ${database} from ${PROJECT_ID}"
       result=1
   fi
done

if [ ${result} -ne 0 ]
then
    echo "At least one error occurred during backup of ${PROJECT_ID}"
fi

exit $result
