# GitHub Repositories Backup

[![codecov](https://codecov.io/gh/vwt-digital/dcat-deploy/branch/develop/graph/badge.svg?token=G1NVNK56D3)](https://codecov.io/gh/vwt-digital/dcat-deploy)

The GitHub Repositories Backup functionality is used to automatically back up multiple GitHub repositories towards a 
Google Cloud Storage bucket. It uses the [GitHub Migrations API](https://docs.github.com/en/rest/reference/migrations) 
to retrieve all repositories with their commits, comments and pull requests.

The files within this directory deploy the following parts:
1. A Cloud Function requesting a GitHub Migration for a GitHub organisation;
2. A Cloud Function downloading a GitHub Migration for a GitHub organisation;
3. A Scheduler that creates a build that creates Cloud Tasks.

### Cloud Functions
#### Request a GitHub migration
The Cloud Function for requesting a GitHub migration will do so based on a GitHub organisation and its repositories.
For a more elaborate explanation, please see the [documentation](github_request_backup/README.md).

#### Download a GitHub migration
The Cloud Function for downloading a GitHub migration will do so based on a GitHub organisation. For a more elaborate 
explanation, please see the [documentation](github_download_backup/README.md).

### Cloud Tasks
The creation of Cloud Tasks will be based on the data-catalog containing all repositories. For each GitHub 
organisation within that catalog two Cloud Tasks will be created by the Cloud Scheduler every morning at 02:00 UTC on 
workdays:
1. A task to request a GitHub organisation migration running immediately after creation;
2. A task to download a GitHub organisation migration running precisely 1 hour after creation.

## License
[GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html)
