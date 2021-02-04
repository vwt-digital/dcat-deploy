# GitHub Download Backup

This function is intented to download a migration backup request from the GitHub API.

## Configuration
These variables have to be defined within the environment of the function:
- `PROJECT_ID` `[string]`: The Project ID of the current GCP project;
- `SECRET_ID` `[string]`: The ID of the Secret Manager secret where the GitHub API Access Token is defined;
- `REPO_BACKUP_BUCKET` `[string]`: The GCS bucket towards where the backup is written (format: `gs://[BUCKET_NAME]`).

## Invoking
The function can be invoked by sending an HTTP-request with the JSON body defined below:
~~~json
{
  "organisation": "ORGANISATION_NAME"
}
~~~
The `ORGANISATION_NAME` value has to be a GitHub organisation that is accessible by the GitHub API Access Token.

## Functionality
1. This function first retrieves the GitHub API Access Token from the Secret Manager secret based on the environment 
   variable `SECRET_ID`;
2. Hereafter, the function will request the archive urls for the migration from the GitHub API;
3. Then for each archive the file will be streamed towards the specified GCS bucket;
4. To finish the process, the function will request a migration deletion from GitHub.
