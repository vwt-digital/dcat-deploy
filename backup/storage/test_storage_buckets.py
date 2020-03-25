import sys
import logging

from google.cloud import storage

logging.getLogger().setLevel(logging.INFO)

client = storage.Client()
for bucket in client.list_buckets():
    blobs = bucket.list_blobs(max_results=1)
    if len(list(blobs)) < 1:
        logging.warning('Bucket contains no blobs')
        sys.exit(0)
