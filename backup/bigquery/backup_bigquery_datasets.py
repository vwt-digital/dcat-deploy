import logging
import argparse
import subprocess

from retry import retry
from datetime import datetime
from dateutil.parser import parse
from google.cloud import storage
from google.cloud import bigquery
from google.api_core.exceptions import ServiceUnavailable

logging.basicConfig(level=logging.INFO, format='%(levelname)7s: %(message)s')


def main(args):

    storage_client = storage.Client()
    bigquery_client = bigquery.Client()
    tables = get_tables(bigquery_client, args.project, args.dataset)

    logging.info('Starting backup for dataset {}'.format(args.dataset))

    for table in tables:

        logging.info('Starting backup for table {}'.format(table))

        partitions = get_partitions(bigquery_client, args.project, args.dataset, table)
        filtered_partitions = filter_partitions(partitions)

        for partition in filtered_partitions:

            partition_date = get_date(partition)
            partition_path = "backup/bigquery/{}/{}/{}".format(args.dataset, table, partition_date)
            partition_name = '{}:{}.{}${}'.format(args.project, args.dataset, table, partition)

            blobs = list_blobs(storage_client, args.bucket, partition_path)

            if not any('schema.json' in blob for blob in blobs):

                logging.info('Starting backup for schema {}'.format(partition))
                schema = get_schema(partition_name)
                schema_file = '{}/schema.json'.format(partition_path, partition_date)
                backup_schema(storage_client, args.bucket, schema_file, schema)

            if not any('.avro' in blob for blob in blobs):

                logging.info('Starting backup for extract {}'.format(partition))
                # Partition files on bucket if extract size is larger than 1 GB
                size = get_partition_size(bigquery_client, partition_name)
                part = "-*" if size >= 1024 * 1024 * 1024 else ""
                partition_file = '{}/extract{}.avro'.format(partition_path, part)
                backup_partition(partition_name, args.bucket, partition_file)

        table_path = "backup/bigquery/{}/{}".format(args.dataset, table)
        backups = list_blobs(storage_client, args.bucket, table_path)
        expired = [backup for backup in backups if not any(get_date(partition) in backup for partition in partitions)]

        logging.info('Removing expired backups for {}'.format(table))
        for backup in expired:
            delete_blob(storage_client, args.bucket, backup)


@retry(ServiceUnavailable, tries=5, delay=5, backoff=2, logger=None)
def list_blobs(client, bucket_name, path):

    bucket = client.get_bucket(bucket_name)
    files = []
    for blob in bucket.list_blobs(prefix=path):
        files.append(blob.name)

    return files


@retry(ServiceUnavailable, tries=5, delay=5, backoff=2, logger=None)
def delete_blob(client, bucket_name, file_name):

    bucket = client.get_bucket(bucket_name)
    bucket.blob(file_name).delete()

    logging.info('Removed {} from {}'.format(file_name, bucket_name))


def get_date(partition):

    return parse(partition).strftime('%Y/%m/%d')


def get_schema(partition_name):

    schema = exec_shell_command([
        'bq', 'show', '--schema',
        partition_name
    ])

    return schema


def backup_schema(client, bucket_name, file_name, schema):

    bucket = client.get_bucket(bucket_name)
    blob = storage.Blob(file_name, bucket)

    blob.upload_from_string(
        schema,
        content_type='application/json'
    )

    logging.info('Backup schema file {}'.format(file_name))


def backup_partition(partition_name, bucket_name, file_name):

    _ = exec_shell_command([
        'bq', 'extract',
        '--destination_format=AVRO',
        '--use_avro_logical_types',
        '--compression=SNAPPY',
        partition_name,
        'gs://{}/{}'.format(bucket_name, file_name)
    ])

    logging.info('Backup partition {}'.format(partition_name))


def filter_partitions(partitions):

    exclusions = ['__UNPARTITIONED__', datetime.utcnow().strftime('%Y%m%d')]

    return [item for item in partitions if item not in exclusions]


def get_partitions(client, project, dataset, table):

    query = """
        SELECT
          partition_id
        FROM [{}.{}.{}$__PARTITIONS_SUMMARY__]""".format(project, dataset, table)

    job_config = bigquery.QueryJobConfig(use_legacy_sql=True)

    results = client.query(query, job_config=job_config)

    return [row.partition_id for row in results]


def get_tables(client, project, dataset):

    query = client.query("""
        SELECT
          table_id
        FROM
          `{}:{}.__TABLES__`""".format(project, dataset))

    results = query.result()

    return [row.table_id for row in results]


def get_partition_size(client, partition_name):

    query = """
        SELECT
          *
        FROM [{}]""".format(partition_name)

    job_config = bigquery.QueryJobConfig(
        use_legacy_sql=True,
        use_query_cache=False,
        dry_run=True
    )

    results = client.query(query, job_config=job_config)

    return results.total_bytes_processed


def exec_shell_command(command):

    logging.info(' '.join(command))
    process = subprocess.run(command, stdout=subprocess.PIPE, universal_newlines=True)

    return process.stdout


def parse_args():
    parser = argparse.ArgumentParser(description='Backup partitioned bigquery datasets')
    parser.add_argument('-p', '--project',
                        required=True,
                        help='name of a gcp project')
    parser.add_argument('-d', '--dataset',
                        required=True,
                        help='name of a bigquery dataset')
    parser.add_argument('-b', '--bucket',
                        required=True,
                        help='name of a backup bucket')
    return parser.parse_args()


if __name__ == '__main__':
    main(parse_args())
