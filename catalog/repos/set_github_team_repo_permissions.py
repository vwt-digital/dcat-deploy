import json
import sys
import requests
import re

if len(sys.argv) >= 2:
    projectsfile = open(sys.argv[1])
    projects = json.load(projectsfile)
    github_access_token = sys.argv[2]

    for ds in projects['dataset']:
        if ds['distribution'][0]['format'] == "gitrepo":
            if 'odrlPolicy' in ds:
                for perm in ds['odrlPolicy']['permission']:
                    print(perm)

                    organisation_name = re.split('/', perm['target'])[0]
                    assignee_group = re.split(':', perm['assignee'])[1]

                    if (perm['action'] == 'write'):
                        github_perm = 'push'
                    if (perm['action'] == 'read'):
                        github_perm = 'pull'
                    if (perm['action'] == 'admin'):
                        github_perm = 'admin'

                    url = "https://api.github.com/orgs/{}/teams".format(organisation_name)

                    headers = {'Authorization': ''}
                    headers['Authorization'] = 'token '+github_access_token

                    r = requests.get(url, headers=headers)

                    for team in r.json():
                        if (team['name'] == assignee_group):

                            url = "https://api.github.com/teams/{}/repos/{}".format(team['id'], perm['target'])

                            headers = {'Authorization': '',
                                       'Accept': 'application/vnd.github.hellcat-preview+json'}
                            headers['Authorization'] = 'token ' + github_access_token

                            payload = {'permission': ''}
                            payload['permission'] = github_perm

                            r = requests.put(url, headers=headers, json=payload)

                            print(r.request.url)
                            print(r)
