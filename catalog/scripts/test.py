import sys
import json


class Context:
    def __init__(self):
        self.properties = {}
        self.env = {
            'project': 'my-gcp-project',
            'project_number': 1000
        }

context = Context()

print(json.dumps(generate_config(context), indent=4))
