import sys
import json
import datetime

data_catalog = sys.argv[1]
old_project_id = sys.argv[2]
new_project_id = sys.argv[3]
service_account = sys.argv[4]

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


with open(data_catalog, 'r') as file:
    catalog = json.load(file)

catalog.pop('backupDestination', None)
catalog.pop('publishDataCatalog', None)

for outer, dataset in enumerate(catalog.get('dataset')):
    dataset.pop('odrlPolicy', None)
    if dataset.get('identifier') == old_project_id + '-dcat-deployed-stg':
        catalog.get('dataset').pop(outer)
    for inner, distribution in enumerate(dataset.get('distribution')):
        distribution['backupSource'] = distribution.get('title')
        distribution['title'] = distribution.get('title', '').replace(old_project_id, new_project_id)
        if distribution.get('title') == '{}-firestore-ephemeral-backup-stg'.format(new_project_id):
            dataset.get('distribution').pop(inner)

permissions = [
    {
        "target": "{}-tmp-backup-stg".format(new_project_id),
        "action": "write",
        "assignee": "serviceAccount:{}".format(service_account)
    }
]

catalog.get('dataset').append({
  "identifier": "{}-tmp-backup-stg".format(new_project_id),
  "title": "Storage containing temporary backup deployed to {}".format(new_project_id),
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
  "modified": datetime.datetime.now().strftime("%Y-%m-%d"),
  "spatial": "Netherlands",
  "issued": datetime.datetime.now().strftime("%Y-%m"),
  "distribution": [
    {
      "accessURL": "https://console.cloud.google.com/storage/browser/{}-tmp-backup-stg".format(new_project_id),
      "mediaType": "application/json",
      "deploymentZone": get_deployment_zone(new_project_id),
      "format": "blob-storage",
      "title": "{}-tmp-backup-stg".format(new_project_id),
      "description": "VWT development environment at Google europe-west1 containing data catalog blob storage"
    }
  ],
  "odrlPolicy": {
    "uid": new_project_id,
    "permission": permissions
  }
})

print(json.dumps(catalog, indent=4))
