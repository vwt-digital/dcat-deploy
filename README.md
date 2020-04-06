[![CodeFactor](https://www.codefactor.io/repository/github/vwt-digital/dcat-deploy/badge)](https://www.codefactor.io/repository/github/vwt-digital/dcat-deploy)

# dcat-deploy
Deploy data catalog on cloud infrastructure

Use data catalog as described in [Project Company Data](https://vwt-digital.github.io/project-company-data.github.io/) to deploy datasets to cloud infrastructure.

## Usage

Some prerequisites:
* Availability of gcloud command
* Permissions on the project to create the datasets specified in the data catalog
* Deployment manager should be enabled in the project

To deploy a data catalog, run the [deploy_dcat_gcp.sh](deploy_dcat_gcp.sh) script:
```bash
$ deploy_dcat_gcp.sh data_catalog.json my-gcp-project
```
This will create the datasets as specified in the data_catalog.json file on the GCP project _my-gcp-project_. The scrips requires these parameters:
* data catalog path: Path to the data catalog file
* project_id: Project name of the GCP project deploying to

See [Catalog deployment](deploy-dcat-gcp.md) for more information on the resources created on GCP from the data catalog.

