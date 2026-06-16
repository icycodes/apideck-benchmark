import os
import sys
import requests
import json

def main():
    # Read environment variables
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")
    service_id = "github"

    if not all([api_key, app_id, consumer_id, collection_id, zealt_run_id]):
        print("Error: Missing one or more required environment variables.")
        print(f"APIDECK_API_KEY: {'set' if api_key else 'not set'}")
        print(f"APIDECK_APP_ID: {'set' if app_id else 'not set'}")
        print(f"APIDECK_CONSUMER_ID: {'set' if consumer_id else 'not set'}")
        print(f"APIDECK_ISSUE_TRACKING_COLLECTION_ID: {'set' if collection_id else 'not set'}")
        print(f"ZEALT_RUN_ID: {'set' if zealt_run_id else 'not set'}")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": service_id,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    base_url = "https://unify.apideck.com"

    print("--- STEP 1: Creating Ticket ---")
    ticket_subject = f"[COMMENT-EDIT-DELETE] Test ticket for run {zealt_run_id}"
    ticket_payload = {
        "subject": ticket_subject,
        "description": f"This ticket is created for testing comment edit and delete workflow. Run ID: {zealt_run_id}"
    }
    ticket_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets"
    
    print(f"POST {ticket_url}")
    response = requests.post(ticket_url, headers=headers, json=ticket_payload)
    print("Status:", response.status_code)
    try:
        res_json = response.json()
        print(json.dumps(res_json, indent=2))
    except Exception as e:
        print("Response text:", response.text)
        sys.exit(1)

    if response.status_code not in [200, 201] or "data" not in res_json:
        print("Failed to create ticket")
        sys.exit(1)

    ticket_id = res_json["data"]["id"]
    print(f"Ticket successfully created. Ticket ID: {ticket_id}")

    # Write Ticket ID to log file immediately in case of later failure
    log_path = "/home/user/apideck_task/output.log"
    with open(log_path, "w") as f:
        f.write(f"Ticket ID: {ticket_id}\n")
    print(f"Logged Ticket ID to {log_path}")

    print("\n--- STEP 2: Adding Four Comments ---")
    comment_bodies = [
        f"A-{zealt_run_id}",
        f"B-{zealt_run_id}",
        f"C-{zealt_run_id}",
        f"D-{zealt_run_id}"
    ]
    comment_ids = []

    comments_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}/comments"

    for i, body in enumerate(comment_bodies):
        print(f"Adding Comment {i+1}: {body}")
        payload = {"body": body}
        res = requests.post(comments_url, headers=headers, json=payload)
        print(f"Status: {res.status_code}")
        try:
            comment_res = res.json()
            print(json.dumps(comment_res, indent=2))
            if res.status_code not in [200, 201] or "data" not in comment_res:
                print(f"Failed to add comment {body}")
                sys.exit(1)
            comment_id = comment_res["data"]["id"]
            comment_ids.append(comment_id)
            print(f"Comment {i+1} created with ID: {comment_id}")
        except Exception as e:
            print("Response text:", res.text)
            sys.exit(1)

    print(f"All 4 comments created. IDs: {comment_ids}")

    # Append comment IDs to log
    with open(log_path, "a") as f:
        f.write(f"Created Comment IDs: {', '.join(comment_ids)}\n")

    print("\n--- STEP 3: Editing Comment 2 ---")
    # Comment 2 is at index 1
    comment_2_id = comment_ids[1]
    edit_body = f"B-EDITED-{zealt_run_id}"
    edit_payload = {"body": edit_body}
    edit_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}/comments/{comment_2_id}"
    
    print(f"PATCH {edit_url} with body: {edit_body}")
    res = requests.patch(edit_url, headers=headers, json=edit_payload)
    print(f"Status: {res.status_code}")
    try:
        edit_res = res.json()
        print(json.dumps(edit_res, indent=2))
        if res.status_code not in [200, 201] or "data" not in edit_res:
            print("Failed to edit comment 2")
            sys.exit(1)
        print("Comment 2 successfully edited.")
    except Exception as e:
        print("Response text:", res.text)
        sys.exit(1)

    print("\n--- STEP 4: Deleting Comment 3 ---")
    # Comment 3 is at index 2
    comment_3_id = comment_ids[2]
    delete_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}/comments/{comment_3_id}"
    
    print(f"DELETE {delete_url}")
    res = requests.delete(delete_url, headers=headers)
    print(f"Status: {res.status_code}")
    try:
        if res.status_code in [204]:
            print("Comment 3 successfully deleted (204 No Content).")
        else:
            delete_res = res.json()
            print(json.dumps(delete_res, indent=2))
            if res.status_code not in [200, 201]:
                print("Failed to delete comment 3")
                sys.exit(1)
            print("Comment 3 successfully deleted.")
    except Exception as e:
        print("Response text:", res.text)
        sys.exit(1)

    print("\n--- STEP 5: Verifying Final State ---")
    # Retrieve all comments for this ticket
    retrieved_comments = []
    cursor = None
    while True:
        url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}/comments"
        params = {}
        if cursor:
            params["cursor"] = cursor
        
        print(f"GET {url} with params {params}")
        res = requests.get(url, headers=headers, params=params)
        print(f"Status: {res.status_code}")
        if res.status_code != 200:
            print("Failed to list comments")
            sys.exit(1)
            
        list_res = res.json()
        retrieved_comments.extend(list_res.get("data", []))
        
        next_cursor = list_res.get("meta", {}).get("cursors", {}).get("next")
        if not next_cursor:
            break
        cursor = next_cursor

    print(f"Retrieved {len(retrieved_comments)} comments.")
    for c in retrieved_comments:
        print(f"ID: {c.get('id')}, Body: {c.get('body')}")

    # Verify the remaining comment bodies
    remaining_bodies = {c.get("body") for c in retrieved_comments}
    expected_bodies = {
        f"A-{zealt_run_id}",
        f"B-EDITED-{zealt_run_id}",
        f"D-{zealt_run_id}"
    }

    print(f"Remaining bodies: {remaining_bodies}")
    print(f"Expected bodies: {expected_bodies}")

    if remaining_bodies != expected_bodies:
        print("ERROR: Remaining comment bodies do not match expected bodies!")
        sys.exit(1)

    print("Success: Final state verified successfully!")
    with open(log_path, "a") as f:
        f.write("Status: SUCCESS\n")
        f.write(f"Final Comment Bodies: {', '.join(sorted(list(remaining_bodies)))}\n")

if __name__ == "__main__":
    main()
