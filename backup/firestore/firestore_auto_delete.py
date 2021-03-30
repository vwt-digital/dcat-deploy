import datetime
import json
import logging
import sys

from google.cloud import firestore_v1
from isodate import parse_duration

logging.getLogger().setLevel(logging.INFO)

catalog = json.load(open(sys.argv[1], "r"))
firestore_client = firestore_v1.Client()


def get_temporal_in_days(temporal):
    """
    Transform a temporal to days

    :param temporal: Temporal in ISO 8601 format
    :type temporal: str

    :return: Temporal in days
    :rtype: int
    """

    if temporal and temporal.startswith("P"):
        duration = parse_duration(temporal)
        return duration.days

    return None


def process_distribution(dist, temporal_days):
    """
    Process a dataset distribution

    :param dist: Dataset Distribution
    :type dist: dict
    :param temporal_days: Temporal in days
    :type temporal_days: int
    """

    # Retrieve deployment properties
    try:
        kind = dist["deploymentProperties"]["kind"]
        field = dist["deploymentProperties"]["keyField"]
    except KeyError as e:
        logging.error(
            "Distribution '{}' is missing deployment properties: {}".format(
                dist["title"], str(e)
            )
        )
        return

    # Create Firestore batch
    batch_limit = 500
    batch_has_new_entities = True
    batch_last_reference = None

    count_entities = 0

    # Get query filter
    time_delta = datetime.datetime.now() - datetime.timedelta(days=temporal_days)

    while batch_has_new_entities:
        # Setup query
        query = firestore_client.collection(kind)

        # Add filters to query
        query = query.where(field, "<=", time_delta)
        query = query.order_by(field, "ASCENDING")
        query = query.limit(batch_limit)

        # Start on previous entity if existing
        if batch_last_reference:
            query = query.start_after(batch_last_reference)

        # Retrieve query results
        docs = query.stream()
        if docs:
            # Create batch
            batch = firestore_client.batch()
            docs_list = list(docs)

            # Check if query has more results after
            if len(docs_list) < batch_limit:
                batch_has_new_entities = False
            else:
                batch_last_reference = docs_list[-1]

            # Delete entities in batch
            for doc in docs_list:
                batch.delete(doc.reference)
                count_entities += 1

            # Commit batch
            batch.commit()
        else:
            batch_has_new_entities = False

    logging.info("Deleted total of {} '{}' entities".format(count_entities, kind))


if __name__ == "__main__":
    """
    Delete firestore entities based on a temporal
    """

    # Get datasets with temporal
    datasets_with_temp = [
        dataset for dataset in catalog.get("dataset", []) if "temporal" in dataset
    ]

    if len(datasets_with_temp) == 0:
        logging.info("No datasets with temporal found")
        sys.exit(0)

    for dataset in datasets_with_temp:
        # Get and check dataset temporal
        dataset_temp_days = get_temporal_in_days(dataset["temporal"])
        if not (dataset_temp_days and dataset_temp_days > 0):
            logging.info("Temporal for {} is invalid".format(dataset["identifier"]))
            continue

        # Loop and process each datasets distribution
        for distribution in dataset.get("distribution", []):
            if "firestore-kind" == distribution["format"]:
                process_distribution(dist=distribution, temporal_days=dataset_temp_days)

    sys.exit(0)
