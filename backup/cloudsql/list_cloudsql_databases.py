import json
import sys


json_file = open(sys.argv[1], 'r')
catalog = json.load(json_file)

for entry in catalog['dataset']:
    for dist in entry.get('distribution', []):
        if 'title' in dist and dist.get('format', 'n/a') == 'cloudsql-db':
            # Delimiter between instance and database name for bash handling
            print(dist['deploymentProperties']['instance'] + '|' + dist['deploymentProperties']['name'])
