import sys
import json
import re

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

# Check if GitHub URL is existing and if it has the correct format.
# Format: "https://github.com/<org>/<repo>/blob/<branch>/<path-to-file>".
if 'github_url' in catalog and not re.search(
        r"(?:https://github.com/)(vwt-digital|vwt-digital-config+)(?:/)([\w-]+)(?:/blob/)(master|develop+)(?:/)(.+)",
        catalog['github_url']):
    print("Error: catalog does contain GitHub URL, but not in correct HTML URL format: " +
          "\"https://github.com/<org>/<repo>/blob/<branch>/<path-to-file>\". " +
          "See https://vwtdigital.atlassian.net/l/c/HM6iPX0d for an explanation.")
    sys.exit(1)
elif 'github_url' not in catalog:
    print("Error: catalog does not contain GitHub URL. Add the URL of the data-catalog to the top level dictionary " +
          "as follow: \"github_url\": \"https://github.com/<org>/<repo>/blob/<branch>/<path-to-file>\". " +
          "See https://vwtdigital.atlassian.net/l/c/HM6iPX0d for an explanation.")
    sys.exit(1)
