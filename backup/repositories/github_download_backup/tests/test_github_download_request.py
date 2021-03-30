import json
import os
import unittest
import uuid
from datetime import datetime
from random import SystemRandom
from unittest import mock

import main
import secretmanager

safe_random = SystemRandom()

mock_organisation_name = "test-vwt-digital"  # Set mock GitHub organisation name


class CloudSecretPayload:
    def __init__(self, data):
        self.payload = self.CloudSecretData(data)

    class CloudSecretData:
        def __init__(self, data):
            self.data = data


class TestGitHubDownloadRequest(unittest.TestCase):
    @mock.patch.dict(
        os.environ, {"GOOGLE_CLOUD_PROJECT": "gcp-project"}
    )  # Mock env variables
    @mock.patch("main.requests.get")  # Mock 'requests' module 'get' method.
    def test_get_archive_url(self, mock_get):
        """Mocking using a decorator"""

        mock_get_content_correct_id = int(
            safe_random.randrange(99999)
        )  # Setting an ID for the correct Migration
        mock_get_content_created_at = str(
            datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
        )  # Set current date
        mock_get_content = [
            {
                "id": mock_get_content_correct_id,
                "created_at": mock_get_content_created_at,
                "state": "exported",
            },
            {
                "id": int(safe_random.randrange(99999)),
                "created_at": mock_get_content_created_at,
                "state": "exporting",
            },
        ]  # Create mock request return content

        mock_get.return_value.status_code = 200  # Mock status code of response.
        mock_get.return_value.content = str(
            json.dumps(mock_get_content)
        )  # Mock content of response.

        response = main.GitHubDownloadBackup(None, "").get_archive_url(
            organisation=mock_organisation_name
        )  # Call function to request backup migrations

        # Assert that the request-response cycle contains the correct response.
        self.assertEqual(
            response,
            (
                f"https://api.github.com/orgs/{mock_organisation_name}/migrations/{mock_get_content_correct_id}/archive",
                mock_get_content_correct_id,
            ),
        )

    @mock.patch.dict(
        os.environ, {"GOOGLE_CLOUD_PROJECT": "gcp-project"}
    )  # Mock env variables
    @mock.patch(
        "secretmanager.secretmanager_v1.SecretManagerServiceClient", autospec=True
    )
    def test_secret_manager(self, mock_secret):
        """Mocking using a decorator"""

        secret_value = str(uuid.uuid4())

        mock_secret().secret_version_path.return_value = "secret-version-path"
        mock_secret().access_secret_version.return_value = CloudSecretPayload(
            secret_value.encode("utf-8")
        )

        response = secretmanager.get_secret(
            project_id="test-project", secret_id="test-id"
        )  # Call function to retrieve secret

        # Assert that the request-response cycle returns correct value.
        self.assertEqual(response, secret_value)
