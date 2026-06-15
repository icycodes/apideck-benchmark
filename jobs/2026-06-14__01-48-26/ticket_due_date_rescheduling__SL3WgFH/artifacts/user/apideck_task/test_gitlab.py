import os
import requests
import json

api_key = os.getenv("APIDECK_API_KEY")
app_id = os.getenv("APIDECK_APP_ID")
consumer_id = os.getenv("APIDECK_CONSUMER_ID")
collection_id = os.getenv("APIDECK_ISSUE_TRACKING_COLLECTION_ID")

headers = {
    "Authorization": f"Bearer {api_key}",
    "x-apideck-app-id": app_id,
    "x-apideck-consumer-id": consumer_id,
    "x-apideck-service-id": "REDACTED",
    "Content-Type": "application/json"
}

print("Headers:", {k: (v[:10] + "..." if k == "Authorization" else v) for k, v in headers.items()})
print("Collection ID:", collection_id)

url = "https://unify.apideck.com/issue-tracking/collections"
response = requests.get(url, headers=headers)
print("Status Code:", response.status_code)
try:
    print("Response JSON:", json.dumps(response.json(), indent=2))
except Exception as e:
    print("Response text:", response.text)
