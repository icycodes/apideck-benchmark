import os
import requests
import json
from apideck_unify import Apideck

api_key = os.environ.get("APIDECK_API_KEY")
app_id = os.environ.get("APIDECK_APP_ID")
consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
run_id = os.environ.get("ZEALT_RUN_ID")

client = Apideck(
    api_key=api_key,
    app_id=app_id,
    consumer_id=consumer_id
)

file_ids = []

for suffix in ["A", "B", "C"]:
    filename = f"REPORT-{run_id}-{suffix}.txt"
    content = f"This is the content for {filename}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "onedrive",
        "x-apideck-metadata": json.dumps({"name": filename, "parent_folder_id": "root"})
    }

    files = {'file': (filename, content, 'text/plain')}

    print(f"Uploading {filename}...")
    resp = requests.post("https://unify.apideck.com/file-storage/files", headers=headers, files=files)
    if resp.status_code == 201:
        data = resp.json()
        file_id = data["data"]["id"]
        print(f"Uploaded {filename}, id: {file_id}")
        file_ids.append(file_id)
    else:
        print(f"Failed to upload {filename}: {resp.status_code} {resp.text}")
        exit(1)

# Sort file ids ascending
file_ids.sort()

description = "\n".join(file_ids)
subject = f"File Index {run_id} [FILE-INDEX]"

print("Creating ticket...")
try:
    res = client.issue_tracking.collection_tickets.create(
        service_id="github", 
        collection_id=collection_id,
        subject=subject,
        description=description
    )
    print("Ticket created:", res.create_ticket_response.data.id)
except Exception as e:
    print("Error creating ticket:", e)
    exit(1)

print("Done")
