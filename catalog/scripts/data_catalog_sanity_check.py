import sys
import json

catalogfile = open(sys.argv[1], "r")
catalog = json.load(catalogfile)

branch_name = sys.argv[2]
roles = sys.argv[3].split()

services = sys.argv[4].split()
has_datastore_service = True if 'datastore.googleapis.com' in services else False
has_firestore_service = True if 'firestore.googleapis.com' in services else False

has_datastore_dis = False
has_firestore_dis = False

print("Check data_catalog sanity for {}".format(sys.argv[1]))

if 'projectId' not in catalog:
    sys.exit("ERROR: catalog does not contain the projectId." +
             "Solve this by adding the projectId to the catalog.")

for dataset in catalog.get('dataset', []):
    # Check if the permissions are not for users
    if ('odrlPolicy' in dataset and
            'permission' in dataset['odrlPolicy']):
        for perm in dataset['odrlPolicy']['permission']:
            if perm['assignee'].startswith("user:"):
                sys.exit("Error: odrlPolicy contains assignment for a user {}".format(perm))

    # Check if datastore/firestore distributions are within a dataset
    if has_datastore_service or has_firestore_service:
        for distribution in dataset.get('distribution', []):
            if distribution['format'] == 'datastore':
                has_datastore_dis = True
            elif distribution['format'] == 'firestore':
                has_firestore_dis = True

    # Check if viewer role is not applied on projects holding confidential data
    if dataset.get('accessLevel') == 'confidential' and branch_name == 'production':
        if "roles/viewer" in roles:
            sys.exit("ERROR: dataset is confidential and group viewer role is applied." +
                     "Solve this by adding the group to a more limited role than roles/viewer.")

# Make sure a datastore/firestore distribution has been added to the data-catalog if the service is active
if has_datastore_service and not has_datastore_dis:
    sys.exit("ERROR: dataset does not contain Datastore distribution, but project has Datastore API enabled. " +
             "Solve this by either adding a Datastore distribution to the dataset or disabling the Datastore API.")

elif has_firestore_service and not has_firestore_dis:
    sys.exit("ERROR: dataset does not contain Firestore distribution, but project has Firestore API enabled. " +
             "Solve this by either adding a Firestore distribution to the dataset or disabling the Firestore API.")
