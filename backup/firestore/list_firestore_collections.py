from google.cloud import firestore_v1

client = firestore_v1.Client()
collections = client.collections()
for collection in collections:
    print(collection.id)
