import json
import sys
import yaml

catalogfile = open(sys.argv[1], "r")
catalog = json.load(catalogfile)
indexes = []

for dataset in catalog['dataset']:
    for distribution in dataset['distribution']:
        if distribution['format'] == 'datastore-index':
            if 'deploymentProperties' in distribution:
                indexes.append(distribution['deploymentProperties'])

if indexes:
    print(yaml.dump({'indexes': indexes}))

