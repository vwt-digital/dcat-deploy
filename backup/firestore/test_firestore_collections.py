import logging

from google.cloud import firestore_v1
from google.api_core import exceptions

logging.getLogger().setLevel(logging.INFO)

try:
    client = firestore_v1.Client()
    collections = client.collections()
    colls = [coll.id for coll in collections]

    if len(colls) > 0:
        documents = client.collection(colls[0]).limit(1).stream()
        results = [doc.to_dict() for doc in documents]
        for item in results:
            if not isinstance(item, dict):
                raise TypeError("Item must be a JSON")

except exceptions.FailedPrecondition as e:
    logging.info(str(e))
    pass
except Exception as e:
    logging.exception(e)
