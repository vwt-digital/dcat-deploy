import sys
import logging

from google.cloud import storage

logging.getLogger().setLevel(logging.INFO)

bucket_name = sys.argv[1]

client = storage.Client()
bucket = client.get_bucket(bucket_name)
blobs = bucket.list_blobs(max_results=1)
if len(list(blobs)) < 1:
    logging.warning('Bucket {} contains no blobs'.format(bucket.name))
    sys.exit(0)
else:
    logging.info(' + Bucket {} OK!'.format(bucket.name))
