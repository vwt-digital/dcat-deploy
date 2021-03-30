import datetime
import json
import logging
import sys

from google.cloud import datastore
from isodate import parse_duration

logging.getLogger().setLevel(logging.INFO)

catalog = json.load(open(sys.argv[1], "r"))
datastore_client = datastore.Client()


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

    # Create Datastore batch & query
    batch = datastore_client.batch()
    query = datastore_client.query(kind=kind)

    # Set filters on query
    time_delta = (
        datetime.datetime.now() - datetime.timedelta(days=temporal_days)
    ).isoformat()
    query.add_filter(field, "<=", time_delta)
    query.keys_only()

    # Retrieve query results
    entities = list(query.fetch())

    if len(entities) == 0:
        logging.info("No deletable '{}' entities found".format(kind))
        return

    # Begin batch
    batch.begin()
    batch_count = 0
    batch_count_total = 0

    for entity in entities:
        # Commit batch if full (max: 500)
        if batch_count == 500:
            batch.commit()
            batch = datastore_client.batch()
            batch.begin()
            batch_count = 0

        # Add entity to batch
        batch.delete(entity.key)
        batch_count += 1
        batch_count_total += 1

    # Commit batch
    batch.commit()
    logging.info("Deleted total of {} '{}' entities".format(batch_count_total, kind))


if __name__ == "__main__":
    """
    Delete Datastore entities based on a temporal
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
            if "datastore-kind" == distribution["format"]:
                process_distribution(dist=distribution, temporal_days=dataset_temp_days)

    sys.exit(0)
