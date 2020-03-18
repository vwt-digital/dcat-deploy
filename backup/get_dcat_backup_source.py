import json
import sys

json_file = open(sys.argv[1], 'r')
title = sys.argv[2]

catalog = json.load(json_file)
for dataset in catalog.get('dataset'):
    for distribution in dataset.get('distribution'):
        if distribution.get('title') == title:
            print(distribution.get('backupSource'))
