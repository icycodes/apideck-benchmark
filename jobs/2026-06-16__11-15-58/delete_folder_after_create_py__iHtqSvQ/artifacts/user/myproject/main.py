import os
import requests

# Read environment variables
APP_ID = os.environ["APIDECK_APP_ID"]
API_KEY = os.environ["APIDECK_API_KEY"]
CONSUMER_ID = os.environ["APIDECK_CONSUMER_ID"]
DRIVE_NAME = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
RUN_ID = os.environ["ZEALT_RUN_ID"]

BASE_URL = "https://unify.apideck.com"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "x-apideck-app-id": APP_ID,
    "x-apideck-consumer-id": CONSUMER_ID,
    "x-apideck-service-id": "onedrive",
    "Content-Type": "application/json",
}

FOLDER_NAME = f"harbor-delete-{RUN_ID}"

# Step 1: Resolve the drive by name
resp = requests.get(f"{BASE_URL}/file-storage/drives", headers=HEADERS)
resp.raise_for_status()
drives_data = resp.json()

drive_id = None
for drive in drives_data.get("data", []):
    if drive.get("name") == DRIVE_NAME:
        drive_id = drive.get("id")
        break

if drive_id is None:
    raise RuntimeError(f"Drive with name '{DRIVE_NAME}' not found. Available drives: {drives_data}")

# Step 2: Create a folder in the drive root
create_payload = {
    "name": FOLDER_NAME,
    "parent_folder_id": "root",
    "drive_id": drive_id,
}

resp = requests.post(f"{BASE_URL}/file-storage/folders", headers=HEADERS, json=create_payload)
resp.raise_for_status()
folder_data = resp.json()

folder_id = folder_data.get("data", {}).get("id")
if not folder_id:
    raise RuntimeError(f"Unexpected create folder response: {folder_data}")

# Step 3: Delete the folder
resp = requests.delete(f"{BASE_URL}/file-storage/folders/{folder_id}", headers=HEADERS)
resp.raise_for_status()

# Step 4: Write the log file
log_path = "/home/user/myproject/output.log"
with open(log_path, "a") as f:
    f.write(f"Drive ID: {drive_id}\n")
    f.write(f"Created folder ID: {folder_id}\n")
    f.write(f"Deleted folder ID: {folder_id}\n")

print("Done. Log written to", log_path)