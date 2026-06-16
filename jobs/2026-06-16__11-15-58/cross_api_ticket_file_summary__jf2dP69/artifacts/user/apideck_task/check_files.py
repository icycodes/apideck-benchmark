import os
import requests

api_key = os.environ.get("APIDECK_API_KEY")
app_id = os.environ.get("APIDECK_APP_ID")
consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
run_id = os.environ.get("ZEALT_RUN_ID")

headers = {
    "Authorization": f"Bearer {api_key}",
    "x-apideck-app-id": app_id,
    "x-apideck-consumer-id": consumer_id,
    "x-apideck-service-id": "onedrive"
}

resp = requests.get("https://unify.apideck.com/file-storage/files", headers=headers)
data = resp.json()
print("Total items on page:", len(data.get("data", [])))
print("First item:", data.get("data", [])[0]["name"] if data.get("data") else "None")
