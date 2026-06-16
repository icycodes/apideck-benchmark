import os
from apideck_unify import Apideck

api_key = os.environ.get("APIDECK_API_KEY")
app_id = os.environ.get("APIDECK_APP_ID")
consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")

client = Apideck(
    api_key=api_key,
    app_id=app_id,
    consumer_id=consumer_id
)

try:
    res = client.issue_tracking.collection_tickets.create(
        service_id="github", 
        collection_id=collection_id,
        subject="Test Ticket [FILE-INDEX]",
        description="Test description"
    )
    print(res)
except Exception as e:
    print("Error:", e)
