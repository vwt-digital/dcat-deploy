import json
import logging
import os
from datetime import datetime

import gcs_stream_upload
import requests
import secretmanager
from google.cloud import storage

logging.getLogger().setLevel(logging.INFO)

CHUNK_SIZE = 256 * 1024  # 256KB


class GitHubDownloadBackup:
    def __init__(self, github_access_token, bucket_name):
        self.http_headers = {
            "Authorization": f"token {github_access_token}",
            "Accept": "application/vnd.github.wyandotte-preview+json",
        }

        self.bucket_name = bucket_name.replace("gs://", "")
        self.bucket_prefix = (
            f"backup/github/{datetime.strftime(datetime.utcnow(), '%Y/%m/%d')}"
        )

    def download_backup(self, organisation):
        """
        Stream a GitHub backup towards a GCS bucket
        """

        # Get backup archive urls
        archive_url, archive_id = self.get_archive_url(organisation)

        if archive_url:
            stg_client = storage.Client()

            # Create Streamable upload
            archive_filename = f"{self.bucket_prefix}/{organisation}.tgz"
            archive_filename_uri = f"gs://{self.bucket_name}/{archive_filename}"

            if storage.Blob(
                bucket=stg_client.get_bucket(self.bucket_name), name=archive_filename
            ).exists(stg_client):
                logging.info(
                    f"File for archive {archive_id} already exists: '{archive_filename_uri}'"
                )
                return False

            stream_upload = gcs_stream_upload.GCSObjectStreamUpload(
                client=stg_client,
                bucket_name=self.bucket_name,
                blob_name=archive_filename,
                chunk_size=CHUNK_SIZE,
            )

            # Stream archive towards GCS
            try:
                logging.info(
                    f"Starting download of archive {archive_id} towards '{archive_filename_uri}', "
                    + "this could take some time"
                )

                with requests.get(
                    archive_url, stream=True, headers=self.http_headers
                ) as gh_r:
                    gh_r.raise_for_status()
                    stream_upload.start()
                    for chunk in gh_r.iter_content(chunk_size=CHUNK_SIZE):
                        stream_upload.write(chunk)
            except requests.exceptions.ReadTimeout as e:
                logging.error(
                    f"An error occurred when streaming archive {archive_id}: {str(e)}"
                )
                raise
            else:
                stream_upload.stop()
                logging.info(f"Finished download of migration {archive_id}")

                # Let github delete the archive
                try:
                    gh_r = requests.delete(archive_url, headers=self.http_headers)
                    gh_r.raise_for_status()
                except requests.exceptions.RequestException:
                    raise
                else:
                    logging.info(
                        f"Deleted the GitHub archive for migration {archive_id}"
                    )
        else:
            logging.error(f"No migration url for '{organisation}' found")

    def get_archive_url(self, organisation):
        """
        Get the archive url of the latest backup
        """

        github_url = f"https://api.github.com/orgs/{organisation}/migrations?exclude=repositories"

        try:
            # Request backup archive urls
            gh_r = requests.get(github_url, headers=self.http_headers)
        except requests.exceptions.RequestException as e:
            logging.error(
                f"An error occurred during archive url request for '{organisation}': {str(e)}"
            )
            raise
        else:
            if gh_r.ok:
                # Return the archive url of the latest exported migration
                migrations = [
                    {
                        "id": int(migration["id"]),
                        "created_at": datetime.strptime(
                            (migration["created_at"]), "%Y-%m-%dT%H:%M:%S.%f%z"
                        ),
                        "state": migration["state"],
                    }
                    for migration in json.loads(gh_r.content)
                ]

                migrations.sort(key=lambda x: x["created_at"], reverse=True)

                for migration in migrations:
                    if (
                        migration["created_at"].date() == datetime.utcnow().date()
                        and migration["state"] == "exported"
                    ):
                        logging.info(
                            f"Found migration {migration['id']} for '{organisation}'"
                        )

                        return (
                            f"https://api.github.com/orgs/{organisation}/migrations/{migration['id']}/archive",
                            migration["id"],
                        )
            else:
                logging.error(
                    f"Migration request for '{organisation}' failed with status code "
                    + f"{gh_r.status_code}: {str(gh_r.reason)}"
                )

            return None, None


def github_download_backup(request):
    """
    Download a backup export from GitHub
    """

    request_json = request.get_json(silent=True)

    if (
        request_json
        and "organisation" in request_json
        and "PROJECT_ID" in os.environ
        and "SECRET_ID" in os.environ
        and "REPO_BACKUP_BUCKET" in os.environ
    ):
        # Set configuration
        project_id = os.environ.get("PROJECT_ID")
        secret_id = os.environ.get("SECRET_ID")
        backup_bucket = os.environ.get("REPO_BACKUP_BUCKET")
        organisation = request_json.get("organisation")

        logging.info(f"Starting migration download for '{organisation}'")

        # Get GitHub access token from Secret Manager
        github_access_token = secretmanager.get_secret(project_id, secret_id)

        # Stream backup towards GCS bucket
        GitHubDownloadBackup(github_access_token, backup_bucket).download_backup(
            organisation
        )

        return "OK", 204
    else:
        logging.error("Function has insufficient configuration")
        return "Bad Request", 400


if __name__ == "__main__":

    class R:
        def __init__(self):
            self.args = {"organisation": "vwt-digital"}

        def get_json(self, silent=True):
            return self.args

    r = R()
    github_download_backup(r)
