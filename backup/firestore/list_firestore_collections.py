import logging

from google.cloud import firestore_v1
from google.api_core import exceptions

try:
    client = firestore_v1.Client()
    collections = client.collections()
    for collection in collections:
        print(collection.id)

except exceptions.FailedPrecondition as e:
    logging.info(str(e))
except Exception as e:
    logging.exception(e)
