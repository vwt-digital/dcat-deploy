import json
import os
import unittest
import uuid
from unittest import mock

import main
import secretmanager
from requests.exceptions import RequestException

mock_organisation_name = "test-vwt-digital"


class CloudSecretPayload:
    def __init__(self, data):
        self.payload = self.CloudSecretData(data)

    class CloudSecretData:
        def __init__(self, data):
            self.data = data


class MockResponse:
    def __init__(self, ok, status_code, reason=None, response=None):
        self.ok = ok
        self.status_code = status_code
        self.reason = reason
        self.response = response

    def ok(self):
        return self.ok

    def status_code(self):
        return self.status_code

    def reason(self):
        return self.reason

    def json(self):
        return self.response


class TestRequestBackup(unittest.TestCase):
    @mock.patch("main.requests.post")  # Mock 'requests' module 'post' method.
    def test_backup_request_successful(self, mock_post):
        """Mocking using a decorator"""

        mock_response_id = str(uuid.uuid4())  # Create a mock response id

        mock_post.return_value = MockResponse(
            ok=True, status_code=201, response={"id": mock_response_id}
        )  # Mock request response value.

        response = main.GitHubRequestBackup(None).request_backup(
            organisation=mock_organisation_name, repositories=["dcat-deploy"]
        )  # Call function to request backup

        # Assert that the request-response cycle contains the correct response id.
        self.assertEqual(response, mock_response_id)

    @mock.patch("main.requests.post")  # Mock 'requests' module 'post' method.
    def test_backup_request_failing_with_exception(self, mock_post):
        """Mocking using a decorator"""

        mock_post.return_value = MockResponse(
            ok=False, status_code=400
        )  # Mock request response value.
        mock_post.side_effect = RequestException(
            "Test raises exception"
        )  # Mock content of response.

        with self.assertRaises(RequestException):
            main.GitHubRequestBackup(None).request_backup(
                organisation=mock_organisation_name, repositories=["dcat-deploy"]
            )  # Call function to request backup

    @mock.patch("main.requests.post")  # Mock 'requests' module 'post' method.
    def test_backup_request_failing_with_response_code(self, mock_post):
        """Mocking using a decorator"""

        mock_post.return_value = MockResponse(
            ok=False, status_code=400, reason="Test returning 400"
        )  # Mock request response value.

        response = main.GitHubRequestBackup(None).request_backup(
            organisation=mock_organisation_name, repositories=["dcat-deploy"]
        )  # Call function to request backup

        # Assert that the request-response cycle contains the correct response id.
        self.assertEqual(response, False)


class TestCatalogParsing(unittest.TestCase):
    @mock.patch("builtins.open")
    def test_catalog_parsing(self, mock_open):
        """Mocking using a decorator"""

        mock_open_data = json.dumps(
            {
                "dataset": [
                    {
                        "distribution": [
                            {
                                "title": f"{mock_organisation_name}/test-repo",
                                "format": "gitrepo",
                            }
                        ]
                    }
                ]
            }
        )
        mock_open.side_effect = mock.mock_open(
            read_data=mock_open_data
        )  # Mock 'file read' value.

        response = main.DataCatalog().get_organisation_repositories(
            organisation=mock_organisation_name, catalog_name=None
        )  # Call function to parse catalog

        # Assert that the request-response cycle returns correct value.
        self.assertEqual(response, [f"{mock_organisation_name}/test-repo"])


class TestSecretManager(unittest.TestCase):
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
