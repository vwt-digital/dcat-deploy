"""
This scripts generates the additional part of a Cloud Tasks queue deployment script
"gcloud tasks queue create/update [X]" within format "gcloud tasks queue create/update [NAME] --quiet [--ADDITIONAL-FLAGS]"
"""

import json
import sys

catalogfile = open(sys.argv[1], "r")
catalog = json.load(catalogfile)
queues = []

for dataset in catalog['dataset']:
    for distribution in dataset['distribution']:
        if distribution['format'] == 'cloudtask-queue':
            queue_deployment = [distribution['title'], '--quiet']

            for key in distribution.get('deploymentProperties', []):
                queue_deployment.append('--{}={}'.format(key, distribution['deploymentProperties'][key]))

            print(' '.join(queue_deployment))
