import logging

from google.cloud import datastore
from google.api_core import exceptions

logging.getLogger().setLevel(logging.INFO)

try:
    client = datastore.Client()
    query = client.query(kind='__kind__')
    query.keys_only()
    kinds = [entity.key.id_or_name for entity in query.fetch()]
    k = []
    for kind in kinds:
        if not (kind.startswith("__") and kind.endswith("__")):
            k.append(kind)

    if len(k) > 0:
        query = client.query(kind=k[0])
        results = list(query.fetch(limit=1))

        for item in results:
            if not isinstance(item, dict):
                raise TypeError("Item must be a JSON")

except exceptions.FailedPrecondition as e:
    logging.warning(str(e))
    pass
except Exception as e:
    logging.exception(e)
