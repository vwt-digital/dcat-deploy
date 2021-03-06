#!/bin/bash

PROJECT_ID=${1}
TOPICS_AND_PERIODS=${2}

# Delete existing topic history jobs
for job in $(gcloud scheduler jobs list  --project="${PROJECT_ID}" --format="value(name)" | grep "history-job$")
do
    echo " + Deleting existing job $job..."
    gcloud scheduler jobs delete "$job" --project="${PROJECT_ID}" --quiet
done

i=0
for pair in ${TOPICS_AND_PERIODS}
do

    topic=$(echo $pair | cut -d'|' -f 1)
    period=$(echo $pair | cut -d'|' -f 2)
    job="${topic}-history-job"

    # Workaround for scheduler INTERNAL 500 error
    skew=$(($i % 15))

    if [[ $period =~ .T[1-4]M$ ]]
    then
        # Workaround for scheduler 12/15 * * * * does not work
        cron="*/15 * * * *"
    elif [[ $period =~ .T[0-9]*M$ ]]
    then
        cron="$skew * * * *"
    else
        cron="$skew 00,06,12,18 * * *"
    fi

    # Create new topic hostory job
    echo " + Creating job ${job}..."
    gcloud scheduler jobs create http "${job}" \
      --schedule="${cron}" \
      --uri="https://europe-west1-${PROJECT_ID}.cloudfunctions.net/${PROJECT_ID}-history-func/" \
      --http-method=POST \
      --oidc-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
      --oidc-token-audience="https://europe-west1-${PROJECT_ID}.cloudfunctions.net/${PROJECT_ID}-history-func" \
      --message-body="${topic}-history-sub" \
      --max-retry-attempts 3 \
      --max-backoff 10s \
      --attempt-deadline 10m

    i=$((i+1))

done
