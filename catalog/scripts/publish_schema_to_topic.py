import json
import argparse
import logging
from google.cloud import pubsub_v1
import sys
from gobits import Gobits
import requests
import os
from io import StringIO
import jsonschema


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
                ref_status = requests.get(ref).status_code
                print('meta data schema status code: {}'.format(ref_status))
                if(ref_status == 200):
                    # Get the reference via the url
                    reference_schema = requests.get(ref).json()
                    # Add the schema to the new schema
                    reference_schema_txt = json.dumps(reference_schema, indent=2)
                    reference_schema_list = reference_schema_txt.split('\n')
                    for i in range(len(reference_schema_list)):
                        # Do not add the beginning '{' and '}'
                        if i != 0 and i != (len(reference_schema_list)-1):
                            # Write the reference schema to the stringio file
                            new_schema.write(reference_schema_list[i])
                else:
                    logging.error('The URL to the reference of {} does not exist anymore'.format(ref))
                    sys.exit(1)
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
                ref_schema_path_exists = os.path.exists(ref_schema_path)
                print("reference schema path exits: {}".format(ref_schema_path_exists))
                # Check if the path to the schema exists in the schemas folder
                if ref_schema_path_exists:
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
                                # Do not add the beginning '{' and '}'
                                if i != 0 and i != (len(reference_schema_list)-1):
                                    # Write the reference schema to the stringio file
                                    new_schema.write(reference_schema_list[i])
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
                    sys.exit(1)
        else:
            # If the line does not contain any references
            # Just write it to the stringio file
            new_schema.write(line)
    return new_schema


def validate_schema(schema, schema_folder_path):
    if '$schema' in schema:
        meta_data_schema_urn = schema['$schema']
        if 'http' in meta_data_schema_urn:
            # Check if the url still works
            meta_data_schema_status = requests.get(meta_data_schema_urn).status_code
            print('Meta data schema status code: {}'.format(meta_data_schema_status))
            if(meta_data_schema_status == 200):
                # Get the schema via the url
                meta_data_schema = requests.get(meta_data_schema_urn).json()
            else:
                logging.error('The URL to the meta_schema of {} does not exist anymore'.format(schema['$schema']))
        elif 'urn' in meta_data_schema_urn:
            # Pull apart the URN
            meta_data_urn_list = meta_data_schema_urn.split("/")
            meta_data_schema_path = schema_folder_path + "/" + meta_data_urn_list[-1]
            # Check if the path to the schema exists in the schemas folder
            meta_data_schema_path_exists = os.path.exists(meta_data_schema_path)
            print('Meta data schema path exists: {}'.format(meta_data_schema_path_exists))
            if meta_data_schema_path_exists:
                with open(meta_data_schema_path, 'r') as f:
                    meta_data_schema = json.load(f)
            else:
                logging.error('The path {} to the meta data schema {} does not exist'.format(
                    meta_data_schema_path, meta_data_schema_urn))
        else:
            logging.error('Cannot validate schema because no meta_data schema is found')
    else:
        if '$id' in schema:
            logging.error('The schema {} does not have a $schema key'.format(
                            schema["$id"]))
        else:
            logging.error('The schema does not have an $id key')
    # Validate the schema agains the meta data schema
    try:
        jsonschema.validate(schema, meta_data_schema)
    except Exception as e:
        logging.exception('Schema is not conform meta data schema' +
                          ' because of {}'.format(e))
        return False
    logging.info('Schema is conform meta data schema')
    print('Schema is conform meta data schema')
    return True


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
    # Path where the schemas are
    schema_folder_path = args.schema_folder
    # Publish every schema message to the topic
    messages_length = len(messages)
    print('Found {} schema messages'.format(messages_length))
    for m in messages:
        if validate_schema(m['schema'], schema_folder_path):
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
        else:
            sys.exit(1)
