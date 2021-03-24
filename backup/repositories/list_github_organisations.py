"""
This scripts creates a comma-separated-list of GitHub organisations based on the data-catalog
"""

import json
import sys

catalogfile = open(sys.argv[1], "r")
catalog = json.load(catalogfile)
organisations = []

for dataset in catalog["dataset"]:
    for distribution in dataset["distribution"]:
        if distribution["format"] == "gitrepo":
            organisations.append(distribution["title"].split("/")[0])

print(",".join(list(set(organisations))))
