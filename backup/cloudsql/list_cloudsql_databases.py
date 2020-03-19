import json
import sys

json_file = open(sys.argv[1], 'r')
catalog = json.load(json_file)

for dataset in catalog.get('dataset', []):
    for distribution in dataset.get('distribution', []):
        if distribution.get('format') == 'cloudsql-db':
            instance = distribution['deploymentProperties']['instance']
            database = distribution.get('title', '')
            print(instance + '|' + database)
