import json
import sys
import os
import google

from google.cloud import firestore_admin_v1

catalogfile = open(sys.argv[1], "r")
catalog = json.load(catalogfile)
project_id = os.environ.get("PROJECT_ID")

fs_client = firestore_admin_v1.FirestoreAdminClient()


def get_order_value(order):
    """
    Returns order value based on google.firestore.admin.v1.Index.IndexField.Order:
        - ORDER_UNSPECIFIED: 0
        - ASCENDING: 1
        - DESCENDING: 2
    """

    if not order:
        return 0
    if order == 'asc':
        return 1
    if order == 'desc':
        return 2

    return order


def generate_indexes():
    """
    Generates Firestore indexes based on the data-catalog
    """

    indexes = []

    for dataset in catalog['dataset']:
        for distribution in dataset['distribution']:
            if distribution['format'] == 'firestore-index':
                if 'deploymentProperties' in distribution:
                    index = {
                        'collection_group': distribution['deploymentProperties'].get('kind'),
                        'field_config': []
                    }

                    for property in distribution['deploymentProperties'].get('properties', []):
                        index['field_config'].append({
                            'field_path': property.get('name'),
                            'order': get_order_value(property['direction'])
                        })

                    if index['collection_group'] and len(index['field_config']) > 0:
                        indexes.append(index)

    return indexes


def delete_obsolete_indexes(deployed_indexes):
    """
    Deletes all obsolete indexes based on the indexes within the deployment
    """

    count_deleted = 0

    # Retrieve existing indexes
    indexes_parent = fs_client.collection_group_path(project=project_id, database="(default)", collection=None)
    current_indexes = fs_client.list_indexes(parent=indexes_parent)

    deployed_indexes_fields = [index['field_config'] for index in deployed_indexes]

    for current_index in current_indexes:
        current_index_fields = [{
            'field_path': field.field_path,
            'order': field.order
        } for field in current_index.fields if field.field_path != '__name__']

        # Check if index fields are within data-catalog index fields
        if current_index_fields not in deployed_indexes_fields:
            fs_client.delete_index(name=current_index.name)
            count_deleted += 1

    return count_deleted


def deploy_indexes():
    """
    Deploys Firestore indexes
    """

    indexes = generate_indexes()  # Retrieve Firestore indexes

    if len(indexes) > 0:
        deployed_indexes = []

        count_deployed = 0
        count_existing = 0

        for index in indexes:
            # Generate the index parent
            index_parent = fs_client.collection_group_path(
                project=project_id, database="(default)", collection=index['collection_group'])

            # Create a list of index field objects
            index_fields = [
                firestore_admin_v1.Index().IndexField(field_path=field['field_path'], order=field['order']) for
                field in index['field_config']]

            # Create a index object
            index_obj = firestore_admin_v1.Index(query_scope=1, fields=index_fields)

            # Create an index
            try:
                fs_client.create_index(parent=index_parent, index=index_obj)
            except google.api_core.exceptions.AlreadyExists:
                count_existing += 1
                deployed_indexes.append(index)
                pass
            except Exception as e:
                print(f"ERROR creating Firestore index: {str(e)}")
                continue
            else:
                count_deployed += 1
                deployed_indexes.append(index)

        count_deleted = delete_obsolete_indexes(deployed_indexes)  # Remove obsolete indexes

        print(
            f"Created {count_deployed} new Firestore indexes, {count_existing} already existed " +
            f"and {count_deleted} obsolete were deleted")


deploy_indexes()
