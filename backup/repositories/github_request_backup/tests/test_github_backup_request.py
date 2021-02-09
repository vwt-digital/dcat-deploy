import unittest
import json
import uuid

from unittest.mock import patch
from github_request_backup import main


class TestGitHubBackupRequest(unittest.TestCase):
    @patch('github_request_backup.main.requests.post')  # Mock 'requests' module 'post' method.
    def test_backup_request(self, mock_post):
        """Mocking using a decorator"""

        mock_response_id = str(uuid.uuid4())  # Create a mock response id

        mock_post.return_value.status_code = 201  # Mock status code of response.
        mock_post.return_value.content = \
            str(json.dumps({'id': mock_response_id})).encode('utf-8')  # Mock content of response.

        response = main.GitHubRequestBackup(None).request_backup(
            organisation='vwt-digital', repositories=['dcat-deploy'])  # Call function to request backup

        # Assert that the request-response cycle contains the correct response id.
        self.assertEqual(response, mock_response_id)

    @patch('github_request_backup.main.DataCatalog.get_catalog')
    def test_catalog_parsing(self, mock_open):
        """Mocking using a decorator"""

        mock_open.return_value = {'dataset': [{'distribution': [
            {'title': 'test-vwt-digital/test-repo', 'format': 'gitrepo'}]}]}  # Mock 'get_catalog' return value

        response = main.DataCatalog().get_organisation_repositories(
            organisation='test-vwt-digital', catalog_name=None)  # Call function to parse catalog

        # Assert that the request-response cycle returns correct value.
        self.assertEqual(response, ['test-vwt-digital/test-repo'])
