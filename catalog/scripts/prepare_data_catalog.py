import json
from datetime import datetime
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--data-catalog', required=True)
parser.add_argument('-p', '--project', required=True)
parser.add_argument('-dsa', '--delegated-sa', required=False)
args = parser.parse_args()
data_catalog = args.data_catalog
project = args.project
delegated_sa = None
if args.delegated_sa is not None:
    delegated_sa = args.delegated_sa

catalogfile = open(data_catalog, "r")

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

# Add project local backup bucket
if catalog.get('backupDestination'):
    backup_permissions = []
    for dataset in catalog.get('dataset', []):
        for distribution in dataset.get('distribution', []):
            if distribution.get('format') == 'cloudsql-instance':
                backup_permissions.append({
                    "target": "{}-backup-stg".format(project),
                    "action": "write",
                    "assignee": "serviceAccount:$(ref.{}.serviceAccountEmailAddress)".format(distribution.get('title'))
                })

    catalog.get('dataset', []).append({
      "identifier": "{}-backup".format(project),
      "title": "Storage containing backup for {}".format(project),
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
      "keyword": [],
      "modified": datetime.now().strftime("%Y-%m-%d"),
      "spatial": "Netherlands",
      "issued": "2020-05",
      "distribution": [
        {
          "accessURL": "https://console.cloud.google.com/storage/browser/{}-backup-stg".format(project),
          "mediaType": "application/json",
          "deploymentZone": get_deployment_zone(project),
          "format": "blob-storage",
          "title": "{}-backup-stg".format(project),
          "description": "VWT {} environment at Google {} backup storage".format(get_stage(project), get_deployment_zone(project))
        }
      ],
      "odrlPolicy": {
        "uid": "{}-policy".format(project),
        "permission": backup_permissions
      }
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
            if delegated_sa is not None:
                if "odrlPolicy" in dataset:
                    if "permission" in dataset['odrlPolicy']:
                        delegated_sa_permission = {
                          "target": "{}-history-stg".format(distribution.get('title')),
                          "assignee": "serviceAccount:{}".format(delegated_sa),
                          "action": "read"
                        }
                        dataset['odrlPolicy']['permission'].append(delegated_sa_permission)


print(json.dumps(catalog, indent=4))
