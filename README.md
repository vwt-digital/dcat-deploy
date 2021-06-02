[![CodeFactor](https://www.codefactor.io/repository/github/vwt-digital/dcat-deploy/badge)](https://www.codefactor.io/repository/github/vwt-digital/dcat-deploy)

# dcat-deploy
Deploy data catalog on cloud infrastructure

Use data catalog as described in [Project Company Data](https://vwt-digital.github.io/project-company-data.github.io/) to deploy datasets to cloud infrastructure.

## Usage

Some prerequisites:
* Availability of gcloud command
* Permissions on the project to create the datasets specified in the data catalog
* Deployment manager should be enabled in the project

There are 2 options for using the dcat-deploy script:

## With positional arguments

To deploy a data catalog, run the [deploy_dcat_gcp.sh](deploy_dcat_gcp.sh) script:
```bash
$ deploy_dcat_gcp.sh data_catalog.json my-gcp-project
```

## With optional arguments

To deploy a data catalog, run the [deploy_dcat_gcp.sh](deploy_dcat_gcp.sh) script (check the shell script for all possible options):
```bash
$ deploy_dcat_gcp.sh data_catalog.json my-gcp-project -e [ENVIRONMENT_URL]
```

This will create the datasets as specified in the data_catalog.json file on the GCP project _my-gcp-project_. The scrips requires these parameters:
* data catalog path: Path to the data catalog file
* project_id: Project name of the GCP project deploying to

See [Catalog deployment](deploy-dcat-gcp.md) for more information on the resources created on GCP from the data catalog.

### Data Catalog Publish Config
The data catalog can also be published to a topic. In order for this to work, the field *publishDataCatalog* has to be set in the data catalog. This field is as follows:

```
"publishDataCatalog": {
    "topic": "topic-name",
    "project": "project-name"
}
```

[Here](https://github.com/vwt-digital/project-company-data.github.io/blob/develop/v1.1/examples/catalog-sample.json) an example of a data catalog can be found.

### Schemas
When the data catalog contains a dataset that has a *topic* distribution, it is highly recommended to send a schema along with the topic. This can be done by adding the fields *describedBy* and *describedByType* to the distribution. The value of *describedBy* should be the file name of the schema and the value of *describedByType* should be the type of the schema, for JSON schemas this is *application/schema+json*.

The data catalog deployment needs to know where the schemas are and to what topic the schemas should be send. This is done by giving two extra parameters to [deploy_dcat_gcp.sh](deploy_dcat_gcp.sh). These parameters are:
* schemas folder path: Path where the schemas can be found
* schemas config: Yaml file with information about where the topic is the schemas need to be send to

Here is an example of a schema config yaml:
```
---
config:
    topic_project_id: project-name-containing-topic
    topic_name: topic-name
```
