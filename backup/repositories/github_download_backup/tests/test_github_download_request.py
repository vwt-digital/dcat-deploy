import unittest
import json
import os

import main

from unittest.mock import patch
from random import randrange
from datetime import datetime

mock_organisation_name = 'test-vwt-digital'  # Set mock GitHub organisation name


class TestGitHubDownloadRequest(unittest.TestCase):
    @patch.dict(
        os.environ, {"GOOGLE_CLOUD_PROJECT": "gcp-project",
                     "GOOGLE_APPLICATION_CREDENTIALS": ""})  # Mock env variables
    @patch('main.requests.get')  # Mock 'requests' module 'get' method.
    def test_get_archive_url(self, mock_get):
        """Mocking using a decorator"""

        mock_get_content_correct_id = int(randrange(99999))  # Setting an ID for the correct Migration
        mock_get_content_created_at = str(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f+00:00'))  # Set current date
        mock_get_content = [
            {'id': mock_get_content_correct_id, 'created_at': mock_get_content_created_at, 'state': 'exported'},
            {'id': int(randrange(99999)), 'created_at': mock_get_content_created_at, 'state': 'exporting'}
        ]  # Create mock request return content

        mock_get.return_value.status_code = 200  # Mock status code of response.
        mock_get.return_value.content = str(json.dumps(mock_get_content))  # Mock content of response.

        response = main.GitHubDownloadBackup(None, '').get_archive_url(
            organisation=mock_organisation_name)  # Call function to request backup migrations

        # Assert that the request-response cycle contains the correct response.
        self.assertEqual(
            response,
            (f"https://api.github.com/orgs/{mock_organisation_name}/migrations/{mock_get_content_correct_id}/archive",
             mock_get_content_correct_id))
