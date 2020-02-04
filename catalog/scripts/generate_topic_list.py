import json
import sys


json_file = open(sys.argv[1], 'r')
catalog = json.load(json_file)

for dataset in catalog['dataset']:
    for dist in dataset.get('distribution', []):
        if dist.get('format') == 'topic':
            # Delimiter between instance and database name for bash handling
            print(dist['title'] + '|' + dataset.get('accrualPeriodicity', ''))
