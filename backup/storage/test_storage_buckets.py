import sys
import logging

from google.cloud import storage

logging.getLogger().setLevel(logging.INFO)

bucket_name = sys.argv[1]

client = storage.Client()
bucket = client.get_bucket(bucket_name)
blobs = bucket.list_blobs(max_results=1)
if len(list(blobs)) < 1:
    logging.warning(f'Bucket {bucket.name} contains no blobs')
    sys.exit(0)
