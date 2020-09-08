import json
import argparse
import logging
from google.cloud import pubsub_v1, storage
import sys
from gobits import Gobits
import requests
from functools import reduce
import operator
import os


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
            fill_refs(schema, schema_folder_path)
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


# This function replaces the reference URNs with the actual schema
def fill_refs(schema, schema_folder_path):
    arr = []
    current_prop = ''
    attributes_arr = get_attributes_array(schema, arr, current_prop)
    for att in attributes_arr:
        if att:
            if(att[-2] == "$ref"):
                # Get the URN of the reference
                ref = att[-1]
                reference_schema = {}
                # If the reference is an url
                if (ref.startswith("http")):
                    # Check if the url still works
                    if(requests.get(ref).status_code == 200):
                        # Get the reference via the url
                        reference_schema = requests.get(ref).json()
                        attributes = att[0:len(att)-1]
                        # Set the reference to the right schema
                        setInDict(schema, attributes, reference_schema)
                    else:
                        logging.error('The URL to the reference of {} does not exist anymore'.format(ref))
                # If it is not it's in the schemas folder
                else:
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
                                attributes = att[0:len(att)-1]
                                # Set the reference to the right schema
                                setInDict(schema, attributes, reference_schema)
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


# This function traverses the dictionary and gets the value of a key from a list of attributes
def getFromDict(dataDict, mapList):
    return reduce(operator.getitem, mapList, dataDict)


# This function sets the value of a key from a list of attributes
def setInDict(dataDict, mapList, value):
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value


# This function returns an array of arrays
# The arrays give paths towards an end value,
# e.g. a value that does not contain sub objects
# If the last object contains a reference, this is denoted as "$ref" in the array,
# the reference URN is the last value in the array in that case
# Otherwise the last item in the array will just be "end"
def get_attributes_array(json_object, arr, current_prop):
    # If the attribute properties is in the json object
    if 'properties' in json_object:
        # Iterate over every property and add it to the array
        for prop in json_object['properties']:
            if(current_prop == ''):
                props = ['properties', prop]
            else:
                props = ['properties', current_prop, prop]
            arr.append(props)
            # After it is added to the array, recursively call the function
            # with the current property object
            get_attributes_array(json_object['properties'][prop], arr, prop)
    if 'items' in json_object and 'properties' in json_object['items']:
        # Only if the item has a property object, add the attributes
        for prop in json_object['items']['properties']:
            props = ['properties', current_prop, 'items', 'properties', prop]
            arr.append(props)
            # After it is added to the array, recursively call the function
            # with the current property object
            get_attributes_array(json_object['items']['properties'][prop], arr, prop)
    # If a reference is found in the json object, add it at the end of the attributes array
    if '$ref' in json_object:
        arr[-1].append('$ref')
        arr[-1].append(json_object['$ref'])
    # If there is no properties, items or ref attribute in the json object
    # the function does not have to recurse anymore, the end is found
    else:
        if(arr[-1][-1] != "end" and arr[-1][-2] != "$ref"):
            arr[-1].append("end")
    # At the end of the recursion, return the array
    return arr


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
