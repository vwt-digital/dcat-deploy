import sys
import json

catalogfile = open(sys.argv[1], "r")
catalog = json.load(catalogfile)

services = sys.argv[2].replace('-', '').split() if len(sys.argv) >= 2 else []
has_datastore_service = True if 'datastore.googleapis.com' in services else False
has_firestore_service = True if 'firestore.googleapis.com' in services else False

has_datastore_dis = False
has_firestore_dis = False

print("Check data_catalog sanity for {}".format(sys.argv[1]))

if 'projectId' not in catalog:
    print("Error: catalog does not contain the projectId. Solve this by adding the projectId to the catalog.")
    sys.exit(1)

if 'dataset' in catalog:
    for dataset in catalog['dataset']:
        # Check if the permissions are not for users
        if ('odrlPolicy' in dataset and
                'permission' in dataset['odrlPolicy']):
            for perm in dataset['odrlPolicy']['permission']:
                if perm['assignee'].startswith("user:"):
                    print("Error: odrlPolicy containst assignement for a user {}".format(perm))
                    sys.exit(1)

        # Check if datastore/firestore distributions are within a dataset
        if has_datastore_service or has_firestore_service:
            for distribution in dataset.get('distribution', []):
                if distribution['format'] == 'datastore':
                    has_datastore_dis = True
                elif distribution['format'] == 'firestore':
                    has_firestore_dis = True

    # Make sure a datastore/firestore distribution has been added to the data-catalog if the service is active
    if has_datastore_service and not has_datastore_dis:
        print("Error: dataset does not contain Datastore distribution, but project has Datastore API enabled. " +
              "Solve this by either adding a Datastore distribution to the dataset or disabling the Datastore API.")
        sys.exit(1)
    elif has_firestore_service and not has_firestore_dis:
        print("Error: dataset does not contain Firestore distribution, but project has Firestore API enabled. " +
              "Solve this by either adding a Firestore distribution to the dataset or disabling the Firestore API.")
        sys.exit(1)
