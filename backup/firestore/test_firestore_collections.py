import logging

from google.cloud import firestore_v1
from google.api_core import exceptions

try:
    client = firestore_v1.Client()
    collections = client.collections()
    colls = [coll.id for coll in collections]

    if len(colls) > 0:
        for coll in colls:
            documents = client.collection(coll).limit(1).stream()
            results = [doc.to_dict() for doc in documents]
            for item in results:
                if not isinstance(item, dict):
                    raise TypeError('Item must be a JSON')
                else:
                    logging.info(' + collection {} is OK!'.format(coll))

except exceptions.FailedPrecondition as e:
    logging.info(str(e))
except exceptions.NotFound as e:
    logging.info(str(e))
except Exception as e:
    logging.exception(e)
