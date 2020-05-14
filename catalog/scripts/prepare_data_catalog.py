import sys
import json
from datetime import datetime

catalogfile = open(sys.argv[1], "r")
project = sys.argv[2]

deployment_zones = {
    "gew1": "europe-west1",
    "gew4": "europe-west4"
}

stages = {
    "d": "development",
    "p": "production"
}


def get_stage(project):
    parts = project.split('-')
    if len(parts) > 2:
        return stages.get(parts[1], 'development')
    else:
        return 'development'


def get_deployment_zone(project):
    parts = project.split('-')
    if len(project) > 3:
        return deployment_zones.get(parts[2], 'europe-west1')
    else:
        return 'europe-west1'


catalog = json.load(catalogfile)
catalog.get('dataset', []).append({
  "identifier": "{}-dcat-deployed".format(project),
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
      "name": "VolkerWessels Telecom"
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
      "description": "VWT {} environment at Google europe-west1 containing data catalog blob storage".format(get_stage(project))
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
                "description": "{} history subscription".format(distribution.get('description')),
                "deploymentProperties": {
                  "ackDeadlineSeconds": 600
                }
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

# Add ephemeral backup storage for firestore
for i, dataset in enumerate(catalog.get('dataset', [])):
    for distribution in dataset.get('distribution', []):
        if distribution.get('format') == 'firestore':
            catalog.get('dataset', []).append({
              "identifier": "{}-ephemeral-backup".format(distribution.get('title')),
              "title": "Storage containing firestore ephemeral backup deployed to {}".format(project),
              "accessLevel": "restricted",
              "rights": "The dataset could contain PII, therefore access level is restricted",
              "contactPoint": {
                "fn": "Bernie van Veen",
                "hasEmail": "mailto:b.vanveen@vwt.digital"
              },
              "publisher": {
                "name": "Digital Ambition Team",
                "subOrganizationOf": {
                  "name": "VolkerWessels Telecom"
                }
              },
              "keyword": ["firestore", "backup"],
              "modified": datetime.now().strftime("%Y-%m-%d"),
              "spatial": "Netherlands",
              "temporal": "P7D",
              "issued": "2020-03",
              "distribution": [
                {
                  "accessURL": "https://console.cloud.google.com/storage/browser/{}-firestore-ephemeral-backup-stg".format(project),
                  "mediaType": "application/json",
                  "deploymentZone": get_deployment_zone(project),
                  "format": "blob-storage",
                  "title": "{}-ephemeral-backup-stg".format(distribution.get('title')),
                  "description": "{} ephemeral backup storage".format(distribution.get('description'))
                }
              ]
            })
            break
    else:
        continue
    break

# Add ephemeral backup storage for datastore
for i, dataset in enumerate(catalog.get('dataset', [])):
    for distribution in dataset.get('distribution', []):
        if distribution.get('format') == 'datastore':
            catalog.get('dataset', []).append({
              "identifier": "{}-ephemeral-backup".format(distribution.get('title')),
              "title": "Storage containing datastore ephemeral backup deployed to {}".format(project),
              "accessLevel": "restricted",
              "rights": "The dataset could contain PII, therefore access level is restricted",
              "contactPoint": {
                "fn": "Bernie van Veen",
                "hasEmail": "mailto:b.vanveen@vwt.digital"
              },
              "publisher": {
                "name": "Digital Ambition Team",
                "subOrganizationOf": {
                  "name": "VolkerWessels Telecom"
                }
              },
              "keyword": ["datastore", "backup"],
              "modified": datetime.now().strftime("%Y-%m-%d"),
              "spatial": "Netherlands",
              "temporal": "P7D",
              "issued": "2020-05",
              "distribution": [
                {
                  "accessURL": "https://console.cloud.google.com/storage/browser/{}-datastore-ephemeral-backup-stg".format(project),
                  "mediaType": "application/json",
                  "deploymentZone": get_deployment_zone(project),
                  "format": "blob-storage",
                  "title": "{}-ephemeral-backup-stg".format(distribution.get('title')),
                  "description": "{} ephemeral backup storage".format(distribution.get('description'))
                }
              ]
            })
            break
    else:
        continue
    break

print(json.dumps(catalog, indent=4))
