import logging

from google.cloud import datastore
from google.api_core import exceptions

try:
    client = datastore.Client()
    query = client.query(kind='__kind__')
    query.keys_only()
    kinds = [entity.key.id_or_name for entity in query.fetch()]
    for kind in kinds:
        if not (kind.startswith("__") and kind.endswith("__")):
            print(kind)

except exceptions.FailedPrecondition as e:
    logging.info(str(e))
except Exception as e:
    logging.exception(e)
