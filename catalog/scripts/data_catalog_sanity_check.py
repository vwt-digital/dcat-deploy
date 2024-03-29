import argparse
import json
import os.path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--data-catalog", required=True)
parser.add_argument("-b", "--branch-name", required=True)
parser.add_argument("-r", "--roles", required=True)
parser.add_argument("-s", "--services", required=True)
parser.add_argument("-sf", "--schema-folder", required=False)
args = parser.parse_args()

catalogfile = open(args.data_catalog, "r")
catalog = json.load(catalogfile)

branch_name = args.branch_name
roles = args.roles.split()

services = args.services.split()
has_datastore_service = True if "datastore.googleapis.com" in services else False
has_firestore_service = True if "firestore.googleapis.com" in services else False

has_datastore_dis = False
has_firestore_dis = False

# Path where the schemas are
schema_folder_path = args.schema_folder

print("Check data_catalog sanity for {}".format(args.data_catalog))

if "projectId" not in catalog:
    sys.exit(
        "ERROR: catalog does not contain the projectId."
        + "Solve this by adding the projectId to the catalog."
    )


def apply_firestore_checks(has_datastore_service, has_firestore_service, dataset):
    # Check if datastore/firestore distributions are within a dataset
    global has_datastore_dis
    global has_firestore_dis

    if has_datastore_service or has_firestore_service:
        for distribution in dataset.get("distribution", []):
            if distribution["format"] == "datastore":
                has_datastore_dis = True
            elif distribution["format"] == "firestore":
                has_firestore_dis = True


def apply_confidential_check(dataset, branch_name):
    # Check if viewer role is not applied on projects holding confidential data
    if dataset.get("accessLevel") == "confidential" and branch_name == "master":
        if "roles/viewer" in roles:
            sys.exit(
                "ERROR: dataset is confidential and group viewer role is applied."
                + "Solve this by adding the group to a more limited role than roles/viewer."
            )


def apply_user_check(dataset):
    # Check if the permissions are not for users
    if "odrlPolicy" in dataset and "permission" in dataset["odrlPolicy"]:
        for perm in dataset["odrlPolicy"]["permission"]:
            if perm["assignee"].startswith("user:"):
                sys.exit(
                    "Error: odrlPolicy contains assignment for a user {}".format(perm)
                )


for dataset in catalog.get("dataset", []):
    # Check if the permissions are not for users
    apply_user_check(dataset)

    # Check if datastore/firestore distributions are within a dataset
    apply_firestore_checks(has_datastore_service, has_firestore_service, dataset)

    # Check if viewer role is not applied on projects holding confidential data
    apply_confidential_check(dataset, branch_name)

    # Check if dataset contains a distribution
    for distribution in dataset.get("distribution", []):
        # Check if distribution is a topic
        if distribution.get("format") == "topic":
            # Check if describedBy and describedByType are set
            described_by = distribution.get("describedBy")
            described_by_type = distribution.get("describedByType")
            # If they are not, give error
            if not described_by or not described_by_type:
                sys.exit(
                    "ERROR: topic distribution {} should contain".format(
                        distribution.get("title")
                    )
                    + " 'describedBy' and 'describedByType' fields."
                )
            elif described_by and described_by_type:
                # If they are, check if there is a schema folder
                if schema_folder_path:
                    # Then check if schema can be found in the schema folder
                    # Replace / and :
                    schema_file_name = described_by.replace("tag:", "tag_")
                    schema_file_name = schema_file_name.replace(":", "_")
                    schema_file_name = schema_file_name.replace("/", "_")
                    # Path to schema
                    ref_schema_path = schema_folder_path + "/" + schema_file_name
                    # Check if the path to the schema exists in the schemas folder
                    if not os.path.exists(ref_schema_path):
                        sys.exit(
                            "ERROR: could not find schema {} in schema folder".format(
                                described_by
                            )
                        )
                else:
                    # If there is no schema folder, give error
                    sys.exit(
                        "ERROR: could not find schema folder for tag {}".format(
                            described_by
                        )
                    )

# Make sure a datastore/firestore distribution has been added to the data-catalog if the service is active
if has_datastore_service and not has_datastore_dis:
    sys.exit(
        "ERROR: dataset does not contain Datastore distribution, but project has Datastore API enabled. "
        + "Solve this by either adding a Datastore distribution to the dataset or disabling the Datastore API."
    )

elif has_firestore_service and not has_firestore_dis:
    sys.exit(
        "ERROR: dataset does not contain Firestore distribution, but project has Firestore API enabled. "
        + "Solve this by either adding a Firestore distribution to the dataset or disabling the Firestore API."
    )
