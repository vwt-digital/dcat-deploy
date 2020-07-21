import json
import argparse
import logging
from google.cloud import pubsub_v1
import sys
from gobits import Gobits
import requests
from functools import reduce
import operator
import os

def get_topic_with_schema(args):
    try:
        with open(args.data_catalog, 'r') as f:
            catalog = json.load(f)
        with open(args.schema, 'r') as f:
            schema = json.load(f)
        schema_folder_path = args.schema_folder

        # Check if schema has any references and fill in the references
        fill_refs(schema, schema_folder_path)

        schema_info = {}

        for dataset in catalog['dataset']:
            for dist in dataset.get('distribution', []):
                if dist.get('format') == 'topic':
                    # Get dataset topic only if it has a schema
                    if dist.get('describedBy') and dist.get('describedByType'):
                        # Topic of the schema
                        topic_of_schema = dist.get('title')
                        # Project id of the topic the schema needs to be published to
                        topic_project_id = "blabla"
                        # Topic the schema needs to be published to
                        topic_name = "blabla"
                        # Put it together in a json
                        schema_info = {
                            "topic_project_id": topic_project_id,
                            "topic_name": topic_name,
                            "topic_of_schema": topic_of_schema,
                            "schema": schema
                        }

        return schema_info
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
                # Get the get the URN of the reference
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
                        logging.error(f"The URL to the reference of {ref}" +
                        "does not exist anymore")
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
                        if 'id' in reference_schema:
                            if reference_schema['id'] == ref:
                                attributes = att[0:len(att)-1]
                                # Set the reference to the right schema
                                setInDict(schema, attributes, reference_schema)
                            else:
                                logging.error(f"ID of reference is {ref} while \
                                that of the schema is {reference_schema['id']}")
                        else:
                            logging.error("Reference schema has no ID")
                    else:
                        logging.error("The path to the schema reference does not exist")

# This function traverses the dictionary and gets the value of a key from a list of attributes
def getFromDict(dataDict, mapList):
    return reduce(operator.getitem, mapList, dataDict)

# This function sets the value of a key from a list of attributes
def setInDict(dataDict, mapList, value):
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value

# This function returns an array of arrays
# The arrays give paths towards an end value, 
# e.g. a value that does not contain sub objects
# If the last object contains a references, this is denoted as "$ref" in the array,
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
        # Only if the items has a property object, add the attributes
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
        if( arr[-1][-1] != "end" and arr[-1][-2] != "$ref"):
            arr[-1].append("end")
    # At the end of the recursion, return the array
    return arr

def publish_to_topic(gobits):
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data-catalog', required=True)
    parser.add_argument('-s', '--schema', required=True)
    parser.add_argument('-sf', '--schema-folder', required=True)
    args = parser.parse_args()
    schema = get_topic_with_schema(args)
    print(json.dumps(schema, indent=4, sort_keys=False))
    
    gobits = Gobits()
    return_bool = publish_to_topic(gobits)
    if not return_bool:
        sys.exit(1)