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

if 'dataset' in catalog:
    for dataset in catalog['dataset']:
        if ('odrlPolicy' in dataset and
                'permission' in dataset['odrlPolicy']):
            for perm in dataset['odrlPolicy']['permission']:
                if perm['assignee'].startswith("user:"):
                    print("Error: odrlPolicy containst assignement for a user {}".format(perm))
                    sys.exit(1)

        if has_datastore_service or has_firestore_service:
            for distribution in dataset.get('distribution', []):
                if distribution['format'] == 'datastore':
                    has_datastore_dis = True
                elif distribution['format'] == 'firestore':
                    has_firestore_dis = True

    if has_datastore_service and not has_datastore_dis:
        print("Error: dataset does not contain datastore distribution")
        sys.exit(1)
    elif has_firestore_service and not has_firestore_dis:
        print("Error: dataset does not contain firestore distribution")
        sys.exit(1)
