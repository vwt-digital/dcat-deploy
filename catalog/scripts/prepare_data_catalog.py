import sys
import json
from datetime import datetime

catalogfile = open(sys.argv[1], "r")
project = sys.argv[2]

deploymentZones = {
    "gew1": "europe-west1",
    "gew4": "europe-west4"
}


def get_deployment_zone(projectToGetZoneFor):
    projectNameParts = projectToGetZoneFor.split('-')
    if len(projectNameParts) > 3:
        return deploymentZones.get(projectNameParts[2], 'europe-west1')
    else:
        return 'europe-west1'


catalog = json.load(catalogfile)
catalog['dataset'].append({
  "identifier": "{}-dcat-deployed-stg".format(project),
  "title": "Storage containing data catalog deployed to {}".format(project),
  "accessLevel": "internal",
  "rights": "The dataset contains meta information about data storage, it does not contain PII, therefore access level is internal",
  "contactPoint": {
    "fn": "Bernie van Veen",
    "hasEmail": "mailto:b.vanveen@vwt.digital"
  },
  "publisher": {
    "name": "Digital Ambition Team",
    "subOrganizationOf": {
      "name": "VokerWessels Telecom"
    }
  },
  "keyword": [],
  "modified": datetime.now().strftime("%Y-%m-%d"),
  "spatial": "Netherlands",
  "issued": "2019-06",
  "distribution": [
    {
      "accessURL": "https://console.cloud.google.com/storage/browser/{}-dcat-deployed-stg".format(project),
      "mediaType": "application/json",
      "deploymentZone": get_deployment_zone(project),
      "format": "blob-storage",
      "title": "{}-dcat-deployed-stg".format(project),
      "description": "VWT development environment at Google europe-west1 containing data catalog blob storage"
    }
  ]
})

# Add event history/offload subscription and storage to existing topics
for i, dataset in enumerate(catalog.get('dataset', [])):
    for distribution in dataset.get('distribution', []):
        if distribution.get('format') == 'topic':
            resources_to_append = [
                {
                    "accessURL": "https://console.cloud.google.com/cloudpubsub/subscriptions/{}-history-sub".format(distribution.get('title')),
                    "mediaType": "application/json",
                    "format": "subscription",
                    "title": "{}-history-sub".format(distribution.get('title')),
                    "description": "{} history subscription".format(distribution.get('description'))
                },
                {
                    "accessURL": "https://console.cloud.google.com/storage/browser/{}-history-stg".format(distribution.get('title')),
                    "mediaType": "application/json",
                    "deploymentZone": get_deployment_zone(project),
                    "format": "blob-storage",
                    "title": "{}-history-stg".format(distribution.get('title')),
                    "description": "{} history storage".format(distribution.get('description'))
                }
            ]
            catalog['dataset'][i]['distribution'].extend(resources_to_append)

print(json.dumps(catalog, indent=4))
