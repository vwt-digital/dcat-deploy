import unittest
import json
import uuid
import os

import main
import secretmanager

from unittest import mock
from requests.exceptions import RequestException

mock_organisation_name = 'test-vwt-digital'


class CloudSecretPayload:
    def __init__(self, data):
        self.payload = self.CloudSecretData(data)

    class CloudSecretData:
        def __init__(self, data):
            self.data = data


class TestRequestBackup(unittest.TestCase):
    @mock.patch('main.requests.post')  # Mock 'requests' module 'post' method.
    def test_backup_request_successful(self, mock_post):
        """Mocking using a decorator"""

        mock_response_id = str(uuid.uuid4())  # Create a mock response id

        mock_post.return_value.status_code = 201  # Mock status code of response.
        mock_post.return_value.content = \
            str(json.dumps({'id': mock_response_id})).encode('utf-8')  # Mock content of response.

        response = main.GitHubRequestBackup(None).request_backup(
            organisation=mock_organisation_name, repositories=['dcat-deploy'])  # Call function to request backup

        # Assert that the request-response cycle contains the correct response id.
        self.assertEqual(response, mock_response_id)

    @mock.patch('main.requests.post')  # Mock 'requests' module 'post' method.
    def test_backup_request_failing_with_exception(self, mock_post):
        """Mocking using a decorator"""

        mock_post.return_value.status_code = 400  # Mock status code of response.
        mock_post.side_effect = RequestException('Test raises exception')  # Mock content of response.

        with self.assertRaises(RequestException):
            main.GitHubRequestBackup(None).request_backup(
                organisation=mock_organisation_name, repositories=['dcat-deploy'])  # Call function to request backup

    @mock.patch('main.requests.post')  # Mock 'requests' module 'post' method.
    def test_backup_request_failing_with_response_code(self, mock_post):
        """Mocking using a decorator"""

        mock_post.return_value.status_code = 400  # Mock status code of response.
        mock_post.return_value.ok = False  # Mock ok value of response.
        mock_post.return_value.reason = 'Test returning 400'  # Mock ok value of response.

        response = main.GitHubRequestBackup(None).request_backup(
            organisation=mock_organisation_name, repositories=['dcat-deploy'])  # Call function to request backup

        # Assert that the request-response cycle contains the correct response id.
        self.assertEqual(response, False)


class TestCatalogParsing(unittest.TestCase):
    @mock.patch('builtins.open')
    def test_catalog_parsing(self, mock_open):
        """Mocking using a decorator"""

        mock_open_data = json.dumps({'dataset': [{'distribution': [
            {'title': f"{mock_organisation_name}/test-repo", 'format': 'gitrepo'}]}]})
        mock_open.side_effect = mock.mock_open(read_data=mock_open_data)  # Mock 'file read' value.

        response = main.DataCatalog().get_organisation_repositories(
            organisation=mock_organisation_name, catalog_name=None)  # Call function to parse catalog

        # Assert that the request-response cycle returns correct value.
        self.assertEqual(response, [f"{mock_organisation_name}/test-repo"])


class TestSecretManager(unittest.TestCase):
    @mock.patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "gcp-project"})  # Mock env variables
    @mock.patch("secretmanager.secretmanager_v1.SecretManagerServiceClient", autospec=True)
    def test_secret_manager(self, mock_secret):
        """Mocking using a decorator"""

        secret_value = str(uuid.uuid4())

        mock_secret().secret_version_path.return_value = 'secret-version-path'
        mock_secret().access_secret_version.return_value = CloudSecretPayload(secret_value.encode('utf-8'))

        response = secretmanager.get_secret(
            project_id='test-project', secret_id='test-id')  # Call function to retrieve secret

        # Assert that the request-response cycle returns correct value.
        self.assertEqual(response, secret_value)
