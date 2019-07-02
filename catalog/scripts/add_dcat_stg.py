import sys
import json
from datetime import datetime

catalogfile = open(sys.argv[1], "r")
project=sys.argv[2]

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
      "deploymentZone": "europe-west1",
      "format": "blob-storage",
      "title": "{}-dcat-deployed-stg".format(project),
      "description": "VWT development environment at Google europe-west1 containing data catalog blob storage"
    }
  ]
})
print(json.dumps(catalog, indent=4))
