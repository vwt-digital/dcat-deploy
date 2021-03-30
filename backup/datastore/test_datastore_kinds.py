import logging

from google.api_core import exceptions
from google.cloud import datastore

try:
    client = datastore.Client()
    query = client.query(kind="__kind__")
    query.keys_only()
    kinds = [entity.key.id_or_name for entity in query.fetch()]

    for kind in kinds:
        if not (kind.startswith("__") and kind.endswith("__")):
            query = client.query(kind=kind)
            results = list(query.fetch(limit=1))
            for item in results:
                if not isinstance(item, dict):
                    raise TypeError("Item must be a JSON")
                else:
                    logging.info(" + kind {} is OK!".format(kind))

except exceptions.FailedPrecondition as e:
    logging.info(str(e))
except exceptions.NotFound as e:
    logging.info(str(e))
except Exception as e:
    logging.exception(e)
