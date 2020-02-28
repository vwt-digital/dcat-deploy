import logging

from google.cloud import firestore_v1
from google.api_core import exceptions

logging.getLogger().setLevel(logging.INFO)

try:
    client = firestore_v1.Client()
    collections = client.collections()
    for collection in collections:
        print(collection.id)
except exceptions.FailedPrecondition as e:
    logging.warning(str(e))
    pass
except Exception as e:
    logging.exception(e)
