import json
import argparse
import logging
from google.cloud import pubsub_v1, storage
import sys
from gobits import Gobits
import requests
import os
from io import StringIO


def get_schema_messages(args):
    try:
        with open(args.data_catalog, 'r') as f:
            catalog = json.load(f)
        with open(args.schema, 'r') as f:
            schema = json.load(f)
        schema_folder_path = args.schema_folder

        schema_messages = []
        # Check if the schema has an id
        if '$id' in schema:
            # Check if schema has any references and fill in the references
            schema = fill_refs_new(schema, schema_folder_path)
            contents = schema.getvalue()
            print(contents)
            schema = json.loads(contents)
            # print(schema)
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
    return []


def fill_refs_new(schema, schema_folder_path):
    new_schema = StringIO()
    schema = json.dumps(schema, indent=2)
    # Make schema into list so that every newline can be printed
    schema_list = schema.split('\n')
    for line in schema_list:
        if '$ref' in line:
            if 'http' in line:
                if '"$ref": "' in line:
                    line_array = line.split('"$ref": "')
                elif '"$ref" : "' in line:
                    line_array = line.split('"$ref" : "')
                else:
                    line_array = ''
                ref = line_array[1].replace('\"', '')
                # Check if the url still works
                if(requests.get(ref).status_code == 200):
                    # Get the reference via the url
                    reference_schema = requests.get(ref).json()
                    # Add the schema to the new schema
                    reference_schema_txt = json.dumps(reference_schema, indent=2)
                    reference_schema_list = reference_schema_txt.split('\n')
                    for i in range(len(reference_schema_list)):
                        if i != 0 and i != (len(reference_schema_list)-1):
                            new_schema.write(reference_schema_list[i])
                else:
                    logging.error('The URL to the reference of {} does not exist anymore'.format(ref))
            elif 'urn' in line:
                if '"$ref": "' in line:
                    line_array = line.split('"$ref": "')
                elif '"$ref" : "' in line:
                    line_array = line.split('"$ref" : "')
                else:
                    line_array = ''
                ref = line_array[1].replace('\"', '')
                # Pull apart the URN
                ref_array = ref.split("/")
                ref_schema_path = schema_folder_path + "/" + ref_array[-1]
                # Check if the path to the schema exists in the schemas folder
                if os.path.exists(ref_schema_path):
                    with open(ref_schema_path, 'r') as f:
                        reference_schema = json.load(f)
                    # Double check if the urn of the schema is the same as the
                    # one of the reference
                    if '$id' in reference_schema:
                        if reference_schema['$id'] == ref:
                            # Add the schema to the new schema
                            reference_schema_txt = json.dumps(reference_schema, indent=2)
                            reference_schema_list = reference_schema_txt.split('\n')
                            for i in range(len(reference_schema_list)):
                                if i != 0 and i != (len(reference_schema_list)-1):
                                    new_schema.write(reference_schema_list[i])
                            # for ref_line in reference_schema_list:
                            #     new_schema.write(ref_line)
                        else:
                            logging.error('ID of reference is {} while \
                            that of the schema is {}'.format(
                                ref, reference_schema['$id']
                            ))
                    else:
                        logging.error('Reference schema of reference {} has no ID'.format(ref))
                else:
                    logging.error('The path {} to the schema reference {} does not exist'.format(
                        ref_schema_path, ref))
        else:
            new_schema.write(line)
    return new_schema


def publish_to_topic(msg, topic_that_uses_schema, topic_project_id, topic_name):
    try:
        # Publish to topic
        publisher = pubsub_v1.PublisherClient()
        topic_path = "projects/{}/topics/{}".format(
            topic_project_id, topic_name)
        future = publisher.publish(
            topic_path, bytes(json.dumps(msg).encode('utf-8')))
        future.add_done_callback(
            lambda x: logging.debug('Published schema with URN {} for topic {}'.format(
                                        msg['schema']['$id'], topic_that_uses_schema))
                )
        return True
    except Exception as e:
        logging.exception('Unable to publish schema ' +
                          'to topic because of {}'.format(e))
    return False


def upload_to_storage(schema, bucket_name):
    try:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(bucket_name)
        # Find out if schema is already in bucket
        blobs = storage_client.list_blobs(bucket_name)
        blobs_to_delete = []
        for blob in blobs:
            # If blob is already in bucket
            if blob.name == schema_name_from_urn(schema['$id']):
                # Remove it because it could be an older version of the schema
                blobs_to_delete.append(blob.name)
        for blob_name in blobs_to_delete:
            logging.info('Schema {} is already in storage, deleting'.format(blob_name))
            blob = bucket.blob(blob_name)
            blob.delete()
        # Now add the schema to the storage
        blob = bucket.blob(schema_name_from_urn(schema['$id']))
        blob.upload_from_string(
            data=json.dumps(schema),
            content_type='application/json'
        )
        logging.info('Uploaded schema {} to bucket {}'.format(schema['$id'], bucket_name))
        return True
    except Exception as e:
        logging.exception('Unable to upload schema ' +
                          'to storage because of {}'.format(e))
    return False


def schema_name_from_urn(schema_name):
    schema_name = schema_name.replace('/', '-')
    return schema_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data-catalog', required=True)
    parser.add_argument('-s', '--schema', required=True)
    parser.add_argument('-sf', '--schema-folder', required=True)
    parser.add_argument('-tpi', '--topic-project-id', required=True)
    parser.add_argument('-tn', '--topic-name', required=True)
    parser.add_argument('-b', '--bucket-name', required=True)
    args = parser.parse_args()
    # A message should be send to the schemas topic
    # for every topic that has this schema
    messages = get_schema_messages(args)
    # Project id of the topic the schema needs to be published to
    topic_project_id = args.topic_project_id
    # Topic the schema needs to be published to
    topic_name = args.topic_name
    # Bucket the schema needs to be uploaded to
    bucket_name = args.bucket_name
    # Publish every schema message to the topic
    messages_length = len(messages)
    print('Found {} schema messages'.format(messages_length))
    for m in messages:
        # The gobits of the message
        gobits = Gobits()
        msg = {
            "gobits": [gobits.to_json()],
            "schema": m['schema']
        }
        topic_that_uses_schema = m['topic_that_uses_schema']
        # print(json.dumps(msg, indent=4, sort_keys=False))
        return_bool_publish_topic = publish_to_topic(msg, topic_that_uses_schema, topic_project_id, topic_name)
        if not return_bool_publish_topic:
            sys.exit(1)
        return_bool_upload_blob = upload_to_storage(m['schema'], bucket_name)
        if not return_bool_upload_blob:
            sys.exit(1)
