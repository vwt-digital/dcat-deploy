#!/usr/bin/python3

import json
import argparse
import logging
from google.cloud import pubsub_v1
import sys
from gobits import Gobits


def get_schema_messages(args):
    try:
        with open(args.data_catalog, 'r') as f:
            catalog = json.load(f)
        with open(args.schema, 'r') as f:
            schema = json.load(f)

        schema_messages = []
        # Check if the schema has an id
        if '$id' in schema:
            for dataset in catalog['dataset']:
                for dist in dataset.get('distribution', []):
                    if dist.get('format') == 'topic':
                        # Get dataset topic only if it has a schema
                        if 'describedBy' in dist and 'describedByType' in dist:
                            # Check if the dataset topic has the given schema
                            if(dist.get('describedBy') == schema['$id']):
                                # Return schema
                                topic_that_uses_schema = dist.get('title')
                                schema_and_topic = {
                                    "topic_that_uses_schema": topic_that_uses_schema,
                                    "schema": schema
                                }
                                schema_messages.append(schema_and_topic)
        else:
            logging.error("The given schema has no ID")
        return schema_messages
    except Exception as e:
        logging.exception('Unable to publish schema ' +
                          'because of {}'.format(e))
        sys.exit(1)
    return []


def publish_to_topic(msg, topic_that_uses_schema, topic_project_id, topic_name):
    try:
        # Publish to topic
        publisher = pubsub_v1.PublisherClient()
        topic_path = "projects/{}/topics/{}".format(
            topic_project_id, topic_name)
        future = publisher.publish(
            topic_path, bytes(json.dumps(msg).encode('utf-8')))
        future.add_done_callback(
            lambda x: logging.debug('Published schema with URI {} for topic {}'.format(
                                        msg['schema']['$id'], topic_that_uses_schema))
                )
        return True
    except Exception as e:
        logging.exception('Unable to publish schema ' +
                          'to topic because of {}'.format(e))
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data-catalog', required=True)
    parser.add_argument('-s', '--schema', required=True)
    parser.add_argument('-tpi', '--topic-project-id', required=True)
    parser.add_argument('-tn', '--topic-name', required=True)
    args = parser.parse_args()
    # A message should be send to the schemas topic
    # for every topic that has this schema
    messages = get_schema_messages(args)
    # Project id of the topic the schema needs to be published to
    topic_project_id = args.topic_project_id
    # Topic the schema needs to be published to
    topic_name = args.topic_name
    # Publish every schema message to the topic
    for m in messages:
        # The gobits of the message
        gobits = Gobits()
        msg = {
            "gobits": [gobits.to_json()],
            "schema": m['schema']
        }
        topic_that_uses_schema = m['topic_that_uses_schema']
        print('Publishing schema {} to topic'.format(m['schema']['$id']))
        # print(json.dumps(msg, indent=2, sort_keys=False))
        return_bool_publish_topic = publish_to_topic(msg, topic_that_uses_schema, topic_project_id, topic_name)
        if not return_bool_publish_topic:
            sys.exit(1)
