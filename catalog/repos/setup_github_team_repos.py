import base64
import os
import json
import sys
import requests
import re
from google.cloud import kms_v1

github_access_token_encrypted = base64.b64decode(os.environ['GITHUB_ACCESS_TOKEN_ENCRYPTED'])
kms_client = kms_v1.KeyManagementServiceClient()
crypto_key_name = kms_client.crypto_key_path_path(os.environ['PROJECT_ID'], 'europe-west1', 'github', 'github-access-token')
decrypt_response = kms_client.decrypt(crypto_key_name, github_access_token_encrypted)
github_access_token = decrypt_response.plaintext.decode("utf-8").replace('\n', '')

if len(sys.argv) >= 1:
    projectsfile = open(sys.argv[1])
    projects = json.load(projectsfile)

    for ds in projects['dataset']:
      if ds['distribution'][0]['format'] == "gitrepo":
        if 'odrlPolicy' in ds:
          for perm in ds['odrlPolicy']['permission']: 
            print(perm)

            organisation_name = re.split('/',perm['target'])[0]
            assignee_group = re.split(':',perm['assignee'])[1]

            if (perm['action'] == 'write'):
                github_perm = 'push'
            if (perm['action'] == 'read'):
                github_perm = 'pull'
            if (perm['action'] == 'admin'):
                github_perm = 'admin'
            
            url = f"https://api.github.com/orgs/{organisation_name}/teams"

            headers = {'Authorization': ''}
            headers['Authorization'] = 'token '+github_access_token

            r = requests.get(url, headers=headers)

            for team in r.json():
              if (team['name'] == assignee_group):
                
                 url = f"https://api.github.com/teams/{team['id']}/repos/{perm['target']}"

                 headers = {'Authorization': '',
                            'Accept': 'application/vnd.github.hellcat-preview+json'}
                 headers['Authorization'] = 'token '+github_access_token

                 payload = {'permission':''}
                 payload['permission'] = github_perm

                 r = requests.put(url, headers=headers, json=payload)

                 print(r.request.url)
                 print(r)



