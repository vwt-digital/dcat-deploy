import json
import sys

json_file = open(sys.argv[1], "r")
catalog = json.load(json_file)

print(catalog.get("backupDestination", ""))
