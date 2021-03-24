#!/usr/bin/python3

import argparse
import json
import logging
import sys

from gobits import Gobits
from google.cloud import pubsub_v1


def get_schemas(catalog, schema_list):
    schemas = []
    schema_names = []
    for schema_file in schema_list:
        try:
            with open(schema_file, "r") as f:
                schema = json.load(f)
        except Exception as e:
            logging.exception("Unable to open schema " + "because of {}".format(e))
            sys.exit(1)
        # Check if the schema has an id
        if "$id" in schema:
            schemas.append(schema)
            schema_names.append(schema["$id"])
        else:
            logging.error("The given schema has no ID")
    return schemas, schema_names


def publish_to_topic(msg, schema_names, topic_project_id, topic_name):
    try:
        # Publish to topic
        publisher = pubsub_v1.PublisherClient()
        topic_path = "projects/{}/topics/{}".format(topic_project_id, topic_name)
        future = publisher.publish(topic_path, bytes(json.dumps(msg).encode("utf-8")))
        future.add_done_callback(
            lambda x: logging.debug(
                "Published schemas with tag {}".format(schema_names)
            )
        )
        return True
    except Exception as e:
        logging.exception(
            "Unable to publish schema " + "to topic because of {}".format(e)
        )
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data-catalog", required=True)
    parser.add_argument("-s", "--schemas", nargs="+", required=True)
    parser.add_argument("-tpi", "--topic-project-id", required=True)
    parser.add_argument("-tn", "--topic-name", required=True)
    args = parser.parse_args()
    # Open data catalog
    try:
        with open(args.data_catalog, "r") as f:
            catalog = json.load(f)
    except Exception as e:
        logging.exception("Unable to open catalog " + "because of {}".format(e))
        sys.exit(1)
    # Get schemas list
    schemas_list = args.schemas
    # A message should be send to the schemas topic
    # for every topic that has this schema
    schemas, schema_names = get_schemas(catalog, schemas_list)
    # Project id of the topic the schema needs to be published to
    topic_project_id = args.topic_project_id
    # Topic the schema needs to be published to
    topic_name = args.topic_name
    # Print which schemas are published
    print("Publishing schemas {} to topic".format(schema_names))
    # Publish every schema message to the topic
    # The gobits of the message
    gobits = Gobits()
    msg = {"gobits": [gobits.to_json()], "schemas": schemas}
    # print(json.dumps(msg, indent=2, sort_keys=False))
    # with open('data.json', 'w') as outfile:
    #     json.dump(msg, outfile, indent=2, sort_keys=False)
    return_bool_publish_topic = publish_to_topic(
        msg, schema_names, topic_project_id, topic_name
    )
    if not return_bool_publish_topic:
        sys.exit(1)
