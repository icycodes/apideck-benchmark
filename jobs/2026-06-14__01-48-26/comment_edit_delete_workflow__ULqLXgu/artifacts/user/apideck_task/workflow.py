import os
import sys
import time
import requests

def main():
    # 1. Retrieve environment variables
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    env_collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")

    print("--- Environment Variables ---")
    print(f"APIDECK_APP_ID: {app_id}")
    print(f"APIDECK_CONSUMER_ID: {consumer_id}")
    print(f"APIDECK_ISSUE_TRACKING_COLLECTION_ID: {env_collection_id}")
    print(f"ZEALT_RUN_ID: {zealt_run_id}")
    print("-----------------------------")

    if not all([api_key, app_id, consumer_id, env_collection_id, zealt_run_id]):
        print("Error: Missing required environment variables.", file=sys.stderr)
        sys.exit(1)

    # 2. Dynamically determine the active service ID
    service_id = None
    for sid in ["github", "REDACTED"]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "x-apideck-app-id": app_id,
            "x-apideck-consumer-id": consumer_id,
            "x-apideck-service-id": sid,
            "Content-Type": "application/json"
        }
        try:
            res = requests.get("https://unify.apideck.com/issue-tracking/collections", headers=headers, timeout=15)
            if res.status_code == 200:
                service_id = sid
                print(f"Found active service: {service_id}")
                break
            else:
                print(f"Service {sid} check returned status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Error checking service {sid}: {e}")

    if not service_id:
        print("Error: Could not find any active/authorized service ID.", file=sys.stderr)
        sys.exit(1)

    # Set up base headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": service_id,
        "Content-Type": "application/json"
    }

    # 3. Resolve the collection ID
    print("Resolving collection ID...")
    try:
        res = requests.get("https://unify.apideck.com/issue-tracking/collections", headers=headers, timeout=15)
        res.raise_for_status()
        collections_data = res.json().get("data", [])
        resolved_collection_id = None
        for col in collections_data:
            if col.get("id") == env_collection_id or col.get("name") == env_collection_id:
                resolved_collection_id = col.get("id")
                print(f"Resolved collection ID '{env_collection_id}' to actual ID: {resolved_collection_id}")
                break
        if not resolved_collection_id:
            resolved_collection_id = env_collection_id
            print(f"Could not find matching collection name/id in list. Defaulting to: {resolved_collection_id}")
    except Exception as e:
        print(f"Warning: Failed to list collections: {e}. Defaulting to: {env_collection_id}")
        resolved_collection_id = env_collection_id

    # 4. Create exactly one ticket
    # The subject must contain [COMMENT-EDIT-DELETE] and the current ZEALT_RUN_ID value.
    subject = f"[COMMENT-EDIT-DELETE] {zealt_run_id}"
    ticket_payload = {
        "subject": subject,
        "description": f"Automated test ticket for comment edit and delete workflow. ZEALT_RUN_ID={zealt_run_id}"
    }

    print(f"Creating ticket with subject: '{subject}'...")
    ticket_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets"
    res = requests.post(ticket_url, json=ticket_payload, headers=headers, timeout=15)
    print(f"Create ticket response status: {res.status_code}")
    if res.status_code not in [200, 201]:
        print(f"Error creating ticket: {res.text}", file=sys.stderr)
        sys.exit(1)

    ticket_data = res.json().get("data", {})
    ticket_id = ticket_data.get("id")
    if not ticket_id:
        print(f"Error: Ticket created but no ID returned. Response: {res.json()}", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully created Ticket ID: {ticket_id}")

    # Write the log file immediately so we have it if anything fails later
    log_file_path = "/home/user/apideck_task/output.log"
    with open(log_file_path, "w") as f:
        f.write(f"Ticket ID: {ticket_id}\n")
    print(f"Wrote Ticket ID to {log_file_path}")

    # Small sleep to ensure backend is ready
    time.sleep(2)

    # 5. Add four comments
    comment_bodies = [
        f"A-{zealt_run_id}",
        f"B-{zealt_run_id}",
        f"C-{zealt_run_id}",
        f"D-{zealt_run_id}"
    ]

    comment_ids = []
    comments_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets/{ticket_id}/comments"

    for idx, body in enumerate(comment_bodies, 1):
        print(f"Adding comment {idx}/4: '{body}'...")
        payload = {"body": body}
        res = requests.post(comments_url, json=payload, headers=headers, timeout=15)
        print(f"Add comment {idx} response status: {res.status_code}")
        if res.status_code not in [200, 201]:
            print(f"Error adding comment {idx}: {res.text}", file=sys.stderr)
            sys.exit(1)
        comment_id = res.json().get("data", {}).get("id")
        if not comment_id:
            print(f"Error: Comment {idx} added but no ID returned. Response: {res.json()}", file=sys.stderr)
            sys.exit(1)
        print(f"Comment {idx} ID: {comment_id}")
        comment_ids.append(comment_id)
        time.sleep(1)

    # 6. Edit Comment 2 in place to B-EDITED-<ZEALT_RUN_ID>
    comment2_id = comment_ids[1]
    edited_body = f"B-EDITED-{zealt_run_id}"
    print(f"Editing comment 2 (ID: {comment2_id}) to: '{edited_body}'...")
    edit_url = f"{comments_url}/{comment2_id}"
    res = requests.patch(edit_url, json={"body": edited_body}, headers=headers, timeout=15)
    print(f"Edit comment response status: {res.status_code}")
    if res.status_code not in [200, 201, 204]:
        print(f"Error editing comment: {res.text}", file=sys.stderr)
        sys.exit(1)
    print("Successfully edited comment 2.")
    time.sleep(1)

    # 7. Delete Comment 3 (ID: comment_ids[2])
    comment3_id = comment_ids[2]
    print(f"Deleting comment 3 (ID: {comment3_id})...")
    delete_url = f"{comments_url}/{comment3_id}"
    res = requests.delete(delete_url, headers=headers, timeout=15)
    print(f"Delete comment response status: {res.status_code}")
    if res.status_code not in [200, 204]:
        print(f"Error deleting comment: {res.text}", file=sys.stderr)
        sys.exit(1)
    print("Successfully deleted comment 3.")
    time.sleep(2)

    # 8. Verify the final state
    print("Verifying final comments state...")
    all_comments = []
    next_cursor = None

    while True:
        params = {}
        if next_cursor:
            params["cursor"] = next_cursor
        res = requests.get(comments_url, params=params, headers=headers, timeout=15)
        print(f"List comments response status: {res.status_code}")
        if res.status_code != 200:
            print(f"Error listing comments: {res.text}", file=sys.stderr)
            sys.exit(1)
        
        res_json = res.json()
        all_comments.extend(res_json.get("data", []))
        
        next_cursor = res_json.get("meta", {}).get("cursors", {}).get("next")
        if not next_cursor:
            break

    print(f"Total comments fetched: {len(all_comments)}")
    comment_bodies_fetched = [c.get("body") for c in all_comments]
    print(f"Comment bodies fetched: {comment_bodies_fetched}")

    expected_bodies = {
        f"A-{zealt_run_id}",
        f"B-EDITED-{zealt_run_id}",
        f"D-{zealt_run_id}"
    }

    fetched_set = set(comment_bodies_fetched)
    print(f"Expected bodies: {expected_bodies}")
    print(f"Fetched bodies: {fetched_set}")

    # Check acceptance criteria
    if len(all_comments) != 3:
        print(f"Error: Expected exactly 3 comments, but found {len(all_comments)}", file=sys.stderr)
        sys.exit(1)

    if fetched_set != expected_bodies:
        print("Error: Fetched comment bodies do not match expected set.", file=sys.stderr)
        sys.exit(1)

    for body in [f"B-{zealt_run_id}", f"C-{zealt_run_id}"]:
        if body in fetched_set:
            print(f"Error: Comment body '{body}' should not be present in the remaining comments.", file=sys.stderr)
            sys.exit(1)

    print("Success! All acceptance criteria met.")

if __name__ == "__main__":
    main()
