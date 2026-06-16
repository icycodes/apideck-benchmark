import os
import requests
import json
import sys

# Retrieve environment variables
API_KEY = os.getenv("APIDECK_API_KEY")
APP_ID = os.getenv("APIDECK_APP_ID")
CONSUMER_ID = os.getenv("APIDECK_CONSUMER_ID")
COLLECTION_ID = os.getenv("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
RUN_ID = os.getenv("ZEALT_RUN_ID")

if not all([API_KEY, APP_ID, CONSUMER_ID, COLLECTION_ID, RUN_ID]):
    print("Error: Missing required environment variables.", file=sys.stderr)
    print(f"APIDECK_API_KEY: {'Set' if API_KEY else 'Not Set'}", file=sys.stderr)
    print(f"APIDECK_APP_ID: {'Set' if APP_ID else 'Not Set'}", file=sys.stderr)
    print(f"APIDECK_CONSUMER_ID: {'Set' if CONSUMER_ID else 'Not Set'}", file=sys.stderr)
    print(f"APIDECK_ISSUE_TRACKING_COLLECTION_ID: {'Set' if COLLECTION_ID else 'Not Set'}", file=sys.stderr)
    print(f"ZEALT_RUN_ID: {'Set' if RUN_ID else 'Not Set'}", file=sys.stderr)
    sys.exit(1)

# Headers for both services
headers_base = {
    "Authorization": f"Bearer {API_KEY}",
    "x-apideck-app-id": APP_ID,
    "x-apideck-consumer-id": CONSUMER_ID,
}

# 1. Clean up existing files matching REPORT-${ZEALT_RUN_ID}-[A|B|C].txt
def cleanup_existing_files():
    print("Listing files in OneDrive to clean up any pre-existing files...")
    headers_onedrive = headers_base.copy()
    headers_onedrive["x-apideck-service-id"] = "onedrive"
    
    target_names = {
        f"REPORT-{RUN_ID}-A.txt",
        f"REPORT-{RUN_ID}-B.txt",
        f"REPORT-{RUN_ID}-C.txt"
    }
    
    url = "https://unify.apideck.com/file-storage/files"
    files_to_delete = []
    
    while url:
        response = requests.get(url, headers=headers_onedrive)
        if response.status_code != 200:
            print(f"Error listing files: {response.text}", file=sys.stderr)
            break
        
        data = response.json()
        for item in data.get("data", []):
            if item.get("name") in target_names:
                files_to_delete.append((item.get("name"), item.get("id")))
        
        url = data.get("links", {}).get("next")
        
    for name, file_id in files_to_delete:
        print(f"Deleting pre-existing file: {name} (ID: {file_id})")
        del_url = f"https://unify.apideck.com/file-storage/files/{file_id}"
        del_res = requests.delete(del_url, headers=headers_onedrive)
        if del_res.status_code in (200, 204):
            print(f"Successfully deleted {name}")
        else:
            print(f"Failed to delete {name}: {del_res.text}", file=sys.stderr)

# 2. Upload the three files
def upload_files():
    print("Uploading the three text files to OneDrive root...")
    headers_onedrive_upload = headers_base.copy()
    headers_onedrive_upload["x-apideck-service-id"] = "onedrive"
    headers_onedrive_upload["Content-Type"] = "text/plain"
    
    file_suffixes = ["A", "B", "C"]
    uploaded_file_ids = []
    
    upload_url = "https://upload.apideck.com/file-storage/files"
    
    for suffix in file_suffixes:
        filename = f"REPORT-{RUN_ID}-{suffix}.txt"
        meta = {
            "name": filename,
            "parent_folder_id": "root"
        }
        headers_current = headers_onedrive_upload.copy()
        headers_current["x-apideck-metadata"] = json.dumps(meta)
        
        content = f"This is report {suffix} for run {RUN_ID}."
        
        print(f"Uploading {filename}...")
        response = requests.post(upload_url, headers=headers_current, data=content)
        if response.status_code == 201:
            res_data = response.json()
            file_id = res_data.get("data", {}).get("id")
            print(f"Successfully uploaded {filename} with Apideck ID: {file_id}")
            uploaded_file_ids.append(file_id)
        else:
            print(f"Failed to upload {filename}: {response.text}", file=sys.stderr)
            sys.exit(1)
            
    return uploaded_file_ids

# 3. Clean up any pre-existing tickets with run ID and literal marker [FILE-INDEX]
def cleanup_existing_tickets():
    print("Listing tickets in GitHub to clean up any pre-existing matching tickets...")
    headers_github = headers_base.copy()
    headers_github["x-apideck-service-id"] = "github"
    
    url = f"https://unify.apideck.com/issue-tracking/collections/{COLLECTION_ID}/tickets"
    tickets_to_update = []
    
    while url:
        response = requests.get(url, headers=headers_github)
        if response.status_code != 200:
            print(f"Error listing tickets: {response.text}", file=sys.stderr)
            break
        
        data = response.json()
        for ticket in data.get("data", []):
            subject = ticket.get("subject", "")
            if RUN_ID in subject and "[FILE-INDEX]" in subject:
                tickets_to_update.append(ticket.get("id"))
                
        url = data.get("links", {}).get("next")
        
    for ticket_id in tickets_to_update:
        print(f"Updating pre-existing matching ticket {ticket_id} to remove markers...")
        update_url = f"https://unify.apideck.com/issue-tracking/collections/{COLLECTION_ID}/tickets/{ticket_id}"
        payload = {
            "subject": f"CLEANED-UP-OLD-TICKET-{ticket_id}",
            "status": "closed"
        }
        headers_patch = headers_github.copy()
        headers_patch["Content-Type"] = "application/json"
        
        patch_res = requests.patch(update_url, headers=headers_patch, json=payload)
        if patch_res.status_code == 200:
            print(f"Successfully cleaned up ticket {ticket_id}")
        else:
            print(f"Failed to clean up ticket {ticket_id}: {patch_res.text}", file=sys.stderr)

# 4. Create the final ticket
def create_ticket(file_ids):
    print("Creating the final Issue Tracking ticket in GitHub...")
    headers_github = headers_base.copy()
    headers_github["x-apideck-service-id"] = "github"
    headers_github["Content-Type"] = "application/json"
    
    # Sort the file IDs in ascending order
    sorted_ids = sorted(file_ids)
    description = "\n".join(sorted_ids)
    
    subject = f"Incident reports for run {RUN_ID} [FILE-INDEX]"
    
    payload = {
        "subject": subject,
        "description": description
    }
    
    url = f"https://unify.apideck.com/issue-tracking/collections/{COLLECTION_ID}/tickets"
    response = requests.post(url, headers=headers_github, json=payload)
    if response.status_code == 201:
        res_data = response.json()
        ticket_id = res_data.get("data", {}).get("id")
        print(f"Successfully created ticket with ID: {ticket_id}")
        print("Ticket Subject:", subject)
        print("Ticket Description:")
        print(description)
    else:
        print(f"Failed to create ticket: {response.text}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    cleanup_existing_files()
    uploaded_ids = upload_files()
    cleanup_existing_tickets()
    create_ticket(uploaded_ids)
    print("Task completed successfully!")
