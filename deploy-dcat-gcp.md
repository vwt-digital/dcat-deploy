## 1. Google Cloud Platform Deployment

The Google Cloud Platform (GCP) provides the Deployment Manager to deploy resources to the platform.
The [Project Company Data](https://vwt-digital.github.io/project-company-data.github.io/) schema can be used
to deploy some types of dataset distribution formats using the GCP Deployment Manager. This will result in empty dataset distribution storage location,
(e.g. a blob storage) ready to receive the actual data. The access permissions will be set as specified in the dataset (see below for more information).

The deployment is done using a GCP Deployment Manager template (see [Creating a basic template](https://cloud.google.com/deployment-manager/docs/configuration/templates/create-basic-template))
for more details.
The [deploy_data_catalog.sh](catalog/scripts/deploy_data_catalog.sh) shell script can be used can be used to deploy Project Company Data Schemas.
It will iterate all distributions in the specified catalog, returning a set of resources to be created by GCP Deployment Manager.
A basic example deploying the storage locations in a catalog:
```bash
$ deploy_data_catalog.sh my-catalog-deployment data_catalog.json my-gcp-project
```
This will create a GCP deployment named _my-catalog-deployment_ deploying the distributions specified in the _data_catalog.json_ file in the GCP project _my-gcp-project_.
The script requires three parameters: the name of the deployment, the filename of the file containing the catalog and the id of the project to deploy to.
The data_catalog.json file is a local file containing the Project Company Data [catalog](https://vwt-digital.github.io/project-company-data.github.io/v1.1/schema/catalog.json).


## 2. Supported formats

The format specified by the [format](https://vwt-digital.github.io/project-company-data.github.io/v1.1/schema/#distribution-format) member of the dataset. By setting the value of this member
to one of the formats in the below table, the corresponding resource will be created.
The following table also shows the formats that are supported by the GCP deploy_data_catalog template.

Format                  | Resource
---                     | ---
blob-storage            | GCP Storage bucket
topic                   | GCP Pub/Sub topic
subscription            | GCP Pub/Sub subscription
cloudsql-instance       | GCP Cloud SQL instance
cloudsql-db             | GCP Cloud SQL database
bigquery-dataset        | GCP BigQuery dataset
datastore               | GCP DataStore (no actual components deployed)
datastore-index         | [GCP DataStore composite index](https://cloud.google.com/datastore/docs/concepts/indexes)
firestore               | GCP FireStore (no actual components deployed)
API                     | External API (no actual components deployed)
gitrepo                 | GitHub repository
azure-blob-storage      | Azure Storage bucket (no actual components deployed)


## 3. Access permissions

On deployment of a dataset, the access permissions will be set according to the accessLevel specified by the dataset.

accessLevel             | Resulting permissions
---                     | ---
public                  | Public read, default write, extended with permissions from the odrlPolicy
internal                | Default permissions, extended with permissions from the odrlPolicy
restricted              | Same as internal
confidential            | For blob-storage only permissions specified in the odrlPolicy, for other formats same as internal

Additional permissions can be set using the odrlPolicy field of the dataset. The GCP deployment will set permissions for each distribution according to the accessLevel, as specified above. Additional policies will be added per distribution as specified in the odrlPolicy permission rules. The table below specifies what is specified by the fields of the odrlPolicy permission.

Field                       | Usage
---                         | ---
uid                         | A unique identifier of the policy in the dataset
permission                  | A list of permission rules to be applied by this policy
permission &rarr; target    | The title of the distribution to which this rule applies
permission &rarr; assignee  | The account to assign the permission to, use the identification as specified in the [Google Cloud IAM Policy](https://cloud.google.com/iam/docs/overview#iam_policy)
permission &rarr; action    | The action that is permitted to the assignee on the target, an instance of [Action class](https://www.w3.org/TR/odrl-vocab/#term-Action). See table below for supported actions.

The action that is allowed on the target determines the GCP role assigned to the assignee. Supported actions in GCP deployment are specified in the table below.

Format                  | read                          | write                         | modify
---                     | ---                           | ---                           | ---
blob-storage            | roles/storage.legacyBucketReader, roles/storage.legacyObjectReader |  roles/storage.legacyBucketWriter, roles/storage.legacyObjectOwner | roles/storage.legacyBucketOwner, roles/storage.legacyObjectOwner
topic                   | roles/pubsub.subscriber       | roles/pubsub.publisher        | roles/pubsub.editor
subscription            | roles/pubsub.subscriber       | n/a                           | n/a

Please note that the permissions will be provisioned on the target itself. Additional permissions might be inherited from the project's IAM (e.g. someone having Project Editor role will be able to publish on all topics).
