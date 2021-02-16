# GitHub Request Backup

This function is intented to send a migration backup request towards the GitHub API.

## Configuration
These variables have to be defined within the environment of the function:
- `PROJECT_ID` `[string]`: The Project ID of the current GCP project;
- `SECRET_ID` `[string]`: The ID of the Secret Manager secret where the GitHub API Access Token is defined;
- `CATALOG_FILE_NAME` `[string]`: The file name of the data-catalog file within the Cloud Function.

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
2. Hereafter, the function will retrieve the data-catalog found within the Cloud Function;
3. All repositories based on the following format will be extracted: `[ORGANISATION_NAME]/[REPOSITORY_NAME]`. Only repositories
   matching the request's body `ORGANISATION_NAME` will be extracted;
4. A request will be sent towards the GitHub API to initiate a migration for the organisation (sent within the 
   request's body), and the corresponding repositories (extracted within the previous step). 
