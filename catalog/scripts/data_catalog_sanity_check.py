import sys
import json

catalogfile = open(sys.argv[1], "r")

catalog = json.load(catalogfile)

print("Check data_catalog sanity for {}".format(sys.argv[1]))

if 'dataset' in catalog:
    for dataset in catalog['dataset']:
        if ('odrlPolicy' in dataset and
                'permission' in dataset['odrlPolicy']):
            for perm in dataset['odrlPolicy']['permission']:
                if perm['assignee'].startswith("user:"):
                    print("Error: odrlPolicy containst assignement for a user {}".format(perm))
                    sys.exit(1)
