import argparse
import json
import logging
import sys

from gobits import Gobits
from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO)


def publish_to_topic(args, gobits):
    try:
        with open(args.data_catalog, "r") as f:
            catalog = json.load(f)

        if "publishDataCatalog" in catalog:
            # Project ID of the data catalog
            dc_project_id = args.project_id
            # Project ID where the topic is
            topic_project_id = catalog["publishDataCatalog"]["project"]
            # Topic name
            topic_name = catalog["publishDataCatalog"]["topic"]
            # Publish to topic
            publisher = pubsub_v1.PublisherClient()
            topic_path = "projects/{}/topics/{}".format(topic_project_id, topic_name)
            msg = {"gobits": [gobits.to_json()], "data_catalog": catalog}
            # print(json.dumps(msg, indent=4, sort_keys=True))
            future = publisher.publish(
                topic_path, bytes(json.dumps(msg).encode("utf-8"))
            )
            future.add_done_callback(
                lambda x: logging.debug(
                    "Published data catalog of project "
                    + "with project ID {}".format(dc_project_id)
                )
            )
        return True
    except Exception as e:
        logging.exception(
            "Unable to publish data catalog " + "to topic because of {}".format(e)
        )
        print("Unable to publish data catalog to topic because of {}".format(e))
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data-catalog", required=True)
    parser.add_argument("-p", "--project-id", required=True)
    args = parser.parse_args()
    gobits = Gobits()
    return_bool = publish_to_topic(args, gobits)
    if not return_bool:
        sys.exit(1)
