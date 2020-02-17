import json
import argparse
import logging
from google.cloud import pubsub_v1
import sys


def publish_to_topic(args):
    try:
        with open(args.data_catalog, 'r') as f:
            catalog = json.load(f)

        if "publishDataCatalog" in catalog:
            # Project ID of the data catalog
            dc_project_id = args.project_id
            # Project ID where the topic is
            topic_project_id = catalog['publishDataCatalog']['project']
            # Topic name
            topic_name = catalog['publishDataCatalog']['topic']
            # Publish to topic
            publisher = pubsub_v1.PublisherClient()
            topic_path = f"projects/{topic_project_id}/topics/{topic_name}"
            msg = {
                "gobits": [
                    {}
                ],
                "data_catalog": catalog
            }
            # print(json.dumps(msg, indent=4, sort_keys=True))
            future = publisher.publish(
                topic_path, bytes(json.dumps(msg).encode('utf-8')))
            future.add_done_callback(
                lambda x: logging.debug(
                    f'Published data catalog of project with project ID {dc_project_id}')
            )
        return True
    except Exception as e:
        logging.exception('Unable to publish data catalog to topic because of {}'.format(e))
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data-catalog', required=True)
    parser.add_argument('-p', '--project-id', required=True)
    args = parser.parse_args()
    return_bool = publish_to_topic(args)
    if not return_bool:
        sys.exit(1)
