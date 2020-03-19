import json
import sys

old_project_id = sys.argv[2]
new_project_id = sys.argv[3]

with open(sys.argv[1], 'r') as file:
    catalog = json.load(file)

catalog.pop('backupDestination', None)
catalog.pop('publishDataCatalog', None)

for idx, dataset in enumerate(catalog.get('dataset')):
    dataset.pop('odrlPolicy', None)
    if dataset.get('identifier') == old_project_id + '-dcat-deployed-stg':
        catalog.get('dataset').pop(idx)
    for distribution in dataset.get('distribution'):
        distribution['backupSource'] = distribution.get('title')
        distribution['title'] = distribution.get('title', '').replace(old_project_id, new_project_id)

print(json.dumps(catalog, indent=4))
