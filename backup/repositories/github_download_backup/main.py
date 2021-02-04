import os
import json

import logging
import requests

import secretmanager
import gcs_stream_upload

from datetime import datetime
from google.cloud import storage

logging.getLogger().setLevel(logging.INFO)

stg_client = storage.Client()
CHUNK_SIZE = 256 * 1024  # 256KB


class GitHubDownloadBackup:
    def __init__(self, github_access_token, bucket_name):
        self.http_headers = {
            'Authorization': f"token {github_access_token}",
            'Accept': 'application/vnd.github.wyandotte-preview+json'}

        self.bucket_name = bucket_name.replace('gs://', '')
        self.bucket_prefix = f"backup/github/{datetime.strftime(datetime.utcnow(), '%Y/%m/%d')}"

    def download_backup(self, organisation):
        """
        Stream a GitHub backup towards a GCS bucket
        """

        # Get backup archive urls
        archive_url = self.get_archive_url(organisation)

        if archive_url:
            logging.info(f"Downloading archive '{archive_url}'")

            # Create Streamable upload
            archive_filename = f"{self.bucket_prefix}/{organisation}.tgz"

            if storage.Blob(bucket=stg_client.get_bucket(self.bucket_name), name=archive_filename).exists(stg_client):
                logging.info(f"File already exists (gs://{self.bucket_name}/{archive_filename})")
                return False

            stream_upload = gcs_stream_upload.GCSObjectStreamUpload(
                client=stg_client, bucket_name=self.bucket_name, blob_name=archive_filename, chunk_size=CHUNK_SIZE)

            # Stream archive towards GCS
            try:
                logging.info("Starting download, this could take a while")
                with requests.get(archive_url, stream=True, headers=self.http_headers) as gh_r:
                    gh_r.raise_for_status()
                    stream_upload.start()
                    for chunk in gh_r.iter_content(chunk_size=CHUNK_SIZE):
                        stream_upload.write(chunk)
            except requests.exceptions.ReadTimeout as e:
                logging.error(f"An error occurred when streaming archive: {str(e)}")
                raise
            else:
                stream_upload.stop()
                logging.info("Finished download")

                # Let github delete the archive
                try:
                    gh_r = requests.delete(archive_url, headers=self.http_headers)
                    gh_r.raise_for_status()
                except requests.exceptions.RequestException:
                    raise
                else:
                    logging.info("Deleted the GitHub archive")
        else:
            logging.error("No migration url can be found")

    def get_archive_url(self, organisation):
        """
        Get the archive url of the latest backup
        """

        github_url = f"https://api.github.com/orgs/{organisation}/migrations"

        try:
            # Request backup archive urls
            gh_r = requests.get(github_url, headers=self.http_headers)
            gh_r.raise_for_status()
        except requests.exceptions.RequestException:
            raise
        else:
            # Return the archive url of the latest exported migration
            for migration in json.loads(gh_r.content):
                if migration['state'] == 'exported':
                    return f"https://api.github.com/orgs/{organisation}/migrations/{migration['id']}/archive"

            return None


def github_download_backup(request):
    """
    Download a backup export from GitHub
    """

    request_json = request.get_json(silent=True)

    if request_json and 'organisation' in request_json and 'PROJECT_ID' in os.environ and \
            'SECRET_ID' in os.environ and 'REPO_BACKUP_BUCKET' in os.environ:
        # Set configuration
        project_id = os.environ.get("PROJECT_ID")
        secret_id = os.environ.get("SECRET_ID")
        backup_bucket = os.environ.get("REPO_BACKUP_BUCKET")
        organisation = request.args.get('organisation')

        logging.info(f"Downloading migration archive for {organisation}")

        # Get GitHub access token from Secret Manager
        github_access_token = secretmanager.get_secret(project_id, secret_id)

        # Stream backup towards GCS bucket
        GitHubDownloadBackup(github_access_token, backup_bucket).download_backup(organisation)

        return 'OK', 204
    else:
        logging.error("Function has insufficient configuration")
        return 'Bad Request', 400


if __name__ == '__main__':
    class R:
        def __init__(self):
            self.args = {'organisation': 'vwt-digital'}
    r = R()
    github_download_backup(r)
