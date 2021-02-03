import os
import json

import logging
import requests
import tempfile

import secretmanager

from google.cloud import storage, exceptions as gcp_exceptions

logging.getLogger().setLevel(logging.INFO)


class GitHubRequestBackup:
    def __init__(self, github_access_token):
        self.http_headers = {
            'Authorization': f"token {github_access_token}",
            'Accept': 'application/vnd.github.wyandotte-preview+json'}

    def request_backup(self, organisation, repositories):
        """
        Send a request to GitHub for a backup export
        """

        github_url = f"https://api.github.com/orgs/{organisation}/migrations"

        try:
            # Request backup
            gh_r = requests.post(
                github_url, headers=self.http_headers,
                json={'lock_repositories': False, 'repositories': repositories})
            gh_r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(e)
            raise
        else:
            response = json.loads(gh_r.content.decode('utf-8'))
            with open('gh_request.json', 'w') as json_file:
                json_file.write(json.dumps(response, indent=2, sort_keys=True))


class DataCatalog:
    def __init__(self):
        self.stg_client = storage.Client()

    def get_organisation_repositories(self, organisation, catalog_uri):
        """
        Get the organisation repositories from a data-catalog file
        """

        # Get data-catalog file
        catalog = self.get_catalog(catalog_uri)

        # Find organisation repositories in data-catalog
        repositories = []

        for dataset in catalog.get('dataset', []):
            for distribution in dataset['distribution']:
                if distribution['format'] == 'gitrepo':
                    if '{}/'.format(organisation) in distribution['title']:
                        repositories.append(distribution['title'])

        return repositories

    def get_catalog(self, catalog_uri):
        """
        Get a data-catalog file from a GCS URI
        """

        try:
            # Get data-catalog as JSON object
            with tempfile.TemporaryFile() as temp_file:
                self.stg_client.download_blob_to_file(catalog_uri, temp_file)
                temp_file.seek(0)

                catalog = json.loads(temp_file.read().decode('utf-8'))
        except (gcp_exceptions.NotFound, json.decoder.JSONDecodeError):
            logging.error(f"Data catalog '{catalog_uri}' not found")
            raise
        else:
            return catalog


def github_request_backup(request):
    """
    Request a backup export for GitHub
    """

    if request.args and 'organisation' in request.args and 'PROJECT_ID' in os.environ and 'SECRET_ID' in os.environ:
        # Set configuration
        project_id = os.environ.get("PROJECT_ID")
        secret_id = os.environ.get("SECRET_ID")
        catalog_uri = f"gs://{project_id}-dcat-deployed-stg/data_catalog.json"
        organisation = request.args.get('organisation')

        logging.info(f"Making migration request for {organisation}")

        # Get GitHub access token from Secret Manager
        github_access_token = secretmanager.get_secret(project_id, secret_id)

        # Get organisation repositories from data-catalog
        repositories = DataCatalog().get_organisation_repositories(organisation, catalog_uri)

        # Request backup for organisation repositories
        if repositories:
            GitHubRequestBackup(github_access_token).request_backup(organisation, repositories)

        return 'OK', 204
    else:
        logging.error("Function has insufficient configuration")
        return 'Bad Request', 400


if __name__ == '__main__':
    class R:
        def __init__(self):
            self.args = {'organisation': 'vwt-digital'}
    r = R()
    github_request_backup(r)
