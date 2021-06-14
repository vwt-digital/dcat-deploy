import argparse
import json
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--data-catalog", required=True)
parser.add_argument("-p", "--project", required=True)
args = parser.parse_args()
data_catalog = args.data_catalog
project = args.project

catalogfile = open(data_catalog, "r")

deployment_zones = {"gew1": "europe-west1", "gew4": "europe-west4"}

stages = {"d": "development", "p": "production"}


def get_stage(project):
    parts = project.split("-")
    if len(parts) > 2:
        return stages.get(parts[1], "development")
    else:
        return "development"


def get_deployment_zone(project):
    parts = project.split("-")
    if len(project) > 3:
        return deployment_zones.get(parts[2], "europe-west1")
    else:
        return "europe-west1"


catalog = json.load(catalogfile)
catalog.get("dataset", []).append(
    {
        "identifier": "{}-dcat-deployed".format(project),
        "title": "Storage containing data catalog deployed to {}".format(project),
        "accessLevel": "internal",
        "rights": "The dataset contains meta information about data storage, it does not contain PII, therefore access level is internal",
        "contactPoint": {
            "fn": "Bernie van Veen",
            "hasEmail": "mailto:b.vanveen@vwt.digital",
        },
        "publisher": {
            "name": "Digital Ambition Team",
            "subOrganizationOf": {"name": "VolkerWessels Telecom"},
        },
        "keyword": [],
        "modified": datetime.now().strftime("%Y-%m-%d"),
        "spatial": "Netherlands",
        "issued": "2019-06",
        "distribution": [
            {
                "accessURL": "https://console.cloud.google.com/storage/browser/{}-dcat-deployed-stg".format(
                    project
                ),
                "mediaType": "application/json",
                "deploymentZone": get_deployment_zone(project),
                "format": "blob-storage",
                "title": "{}-dcat-deployed-stg".format(project),
                "description": "VWT {} environment at Google europe-west1 containing data catalog blob storage".format(
                    get_stage(project)
                ),
            }
        ],
    }
)

# Add project local backup bucket
if catalog.get("backupDestination"):
    backup_permissions = []
    for dataset in catalog.get("dataset", []):
        for distribution in dataset.get("distribution", []):
            if distribution.get("format") == "cloudsql-instance":
                backup_permissions.append(
                    {
                        "target": "{}-backup-stg".format(project),
                        "action": "write",
                        "assignee": "serviceAccount:$(ref.{}.serviceAccountEmailAddress)".format(
                            distribution.get("title")
                        ),
                    }
                )

    catalog.get("dataset", []).append(
        {
            "identifier": "{}-backup".format(project),
            "title": "Storage containing backup for {}".format(project),
            "accessLevel": "restricted",
            "rights": "The dataset could contain PII, therefore access level is restricted",
            "contactPoint": {
                "fn": "Bernie van Veen",
                "hasEmail": "mailto:b.vanveen@vwt.digital",
            },
            "publisher": {
                "name": "Digital Ambition Team",
                "subOrganizationOf": {"name": "VolkerWessels Telecom"},
            },
            "keyword": [],
            "modified": datetime.now().strftime("%Y-%m-%d"),
            "spatial": "Netherlands",
            "issued": "2020-05",
            "distribution": [
                {
                    "accessURL": "https://console.cloud.google.com/storage/browser/{}-backup-stg".format(
                        project
                    ),
                    "mediaType": "application/json",
                    "deploymentZone": get_deployment_zone(project),
                    "format": "blob-storage",
                    "title": "{}-backup-stg".format(project),
                    "description": "VWT {} environment at Google {} backup storage".format(
                        get_stage(project), get_deployment_zone(project)
                    ),
                }
            ],
            "odrlPolicy": {
                "uid": "{}-policy".format(project),
                "permission": backup_permissions,
            },
        }
    )

# Add event history/offload subscription and storage to existing topics
for i, dataset in enumerate(catalog.get("dataset", [])):
    for distribution in dataset.get("distribution", []):
        if distribution.get("format") == "topic":
            resources_to_append = []
            history_storage = {
                "accessURL": "https://console.cloud.google.com/storage/browser/{}-history-stg".format(
                    distribution.get("title")
                ),
                "mediaType": "application/json",
                "deploymentZone": get_deployment_zone(project),
                "format": "blob-storage",
                "title": "{}-history-stg".format(distribution.get("title")),
                "description": "{} history storage".format(
                    distribution.get("description")
                ),
            }
            history_sub = {
                "accessURL": "https://console.cloud.google.com/cloudpubsub/subscriptions/{}-history-sub".format(
                    distribution.get("title")
                ),
                "mediaType": "application/json",
                "format": "subscription",
                "title": "{}-history-sub".format(distribution.get("title")),
                "description": "{} history subscription".format(
                    distribution.get("description")
                ),
                "deploymentProperties": {"ackDeadlineSeconds": 600},
            }
            history_sa = {
                "accessURL": "https://console.cloud.google.com/storage/browser/{}-hst-sa-stg".format(
                    distribution.get("title")
                ),
                "mediaType": "application/json",
                "deploymentZone": get_deployment_zone(project),
                "format": "blob-storage",
                "title": "{}-hst-sa-stg".format(distribution.get("title")),
                "description": "{} history staging storage".format(
                    distribution.get("description")
                ),
                "deploymentProperties": {"defaultEventBasedHold": True},
            }
            lifespan = distribution.get("lifespan")
            if lifespan:
                if lifespan.get("startDate"):
                    # If there is a start date, add a history storage
                    resources_to_append.append(history_storage)
                    # If there is no end date, add the history subscription and history staging bucket
                    end_date = lifespan.get("endDate")
                    if end_date:
                        end_date_string = end_date.split("-")
                        year = int(end_date_string[0])
                        month = int(end_date_string[1])
                        day = int(end_date_string[2])
                        past = datetime(year, month, day)
                        present = datetime.now()
                        check_date = past.date() <= present.date()
                        if check_date is False:
                            resources_to_append.append(history_sub)
                            resources_to_append.append(history_sa)
                    else:
                        resources_to_append.append(history_sub)
                        resources_to_append.append(history_sa)
                    catalog["dataset"][i]["distribution"].extend(resources_to_append)
            # TODO: remove below when every topic has a lifespan
            else:
                resources_to_append = [history_sub, history_storage, history_sa]
                catalog["dataset"][i]["distribution"].extend(resources_to_append)


print(json.dumps(catalog, indent=4))
