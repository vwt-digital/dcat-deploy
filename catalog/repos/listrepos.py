import json
import sys

if len(sys.argv) >= 1:
    projectsfile = open(sys.argv[1])
    projects = json.load(projectsfile)
    for ds in projects["dataset"]:
        if ds["distribution"][0]["format"] == "gitrepo":
            print(json.dumps(ds))
