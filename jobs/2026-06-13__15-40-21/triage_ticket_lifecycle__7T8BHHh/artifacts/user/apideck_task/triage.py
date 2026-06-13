import os
import json
import urllib.request
import urllib.error

def main():
    # 1. Read environment variables
    app_id = os.environ.get("APIDECK_APP_ID")
    api_key = os.environ.get("APIDECK_API_KEY")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")

    print("Checking environment variables...")
    missing = []
    for var, val in [
        ("APIDECK_APP_ID", app_id),
        ("APIDECK_API_KEY", api_key),
        ("APIDECK_CONSUMER_ID", consumer_id),
        ("APIDECK_ISSUE_TRACKING_COLLECTION_ID", collection_id),
        ("ZEALT_RUN_ID", run_id)
    ]:
        if not val:
            missing.append(var)
    if missing:
        print(f"Error: Missing environment variables: {missing}")
        return

    # Set up common headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "github",
        "Content-Type": "application/json"
    }

    base_url = "https://unify.apideck.com"

    # Step 1: Create Ticket
    ticket_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets"
    ticket_subject = f"[triage] login button broken {run_id}"
    ticket_desc = f"Reported by user; affects Safari 17. Triaged via Apideck run {run_id}."
    
    ticket_payload = {
        "subject": ticket_subject,
        "description": ticket_desc,
        "status": "open"
    }
    
    print(f"\nCreating ticket at {ticket_url}...")
    req = urllib.request.Request(
        ticket_url,
        data=json.dumps(ticket_payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            res_data = json.loads(res_body)
            print("Create Ticket Response:")
            print(json.dumps(res_data, indent=2))
            
            ticket_id = res_data.get("data", {}).get("id")
            if not ticket_id:
                raise ValueError("Could not find ticket ID in response data")
            print(f"Successfully created Ticket with ID: {ticket_id}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(e.read().decode("utf-8"))
        return
    except Exception as e:
        print(f"Error creating ticket: {e}")
        return

    # Step 2: Add Comment
    comment_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}/comments"
    comment_payload = {
        "body": "Reproduced and assigned to backend squad. Closing as duplicate of internal report."
    }
    
    print(f"\nAdding comment at {comment_url}...")
    req = urllib.request.Request(
        comment_url,
        data=json.dumps(comment_payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            res_data = json.loads(res_body)
            print("Create Comment Response:")
            print(json.dumps(res_data, indent=2))
            
            comment_id = res_data.get("data", {}).get("id")
            if not comment_id:
                raise ValueError("Could not find comment ID in response data")
            print(f"Successfully created Comment with ID: {comment_id}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(e.read().decode("utf-8"))
        return
    except Exception as e:
        print(f"Error creating comment: {e}")
        return

    # Step 3: Transition Ticket to Closed
    update_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}"
    update_payload = {
        "status": "closed"
    }
    
    print(f"\nUpdating ticket status to closed at {update_url}...")
    req = urllib.request.Request(
        update_url,
        data=json.dumps(update_payload).encode("utf-8"),
        headers=headers,
        method="PATCH"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            res_data = json.loads(res_body)
            print("Update Ticket Response:")
            print(json.dumps(res_data, indent=2))
            print("Successfully closed Ticket.")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(e.read().decode("utf-8"))
        return
    except Exception as e:
        print(f"Error updating ticket: {e}")
        return

    # Write log file
    log_dir = "/home/user/apideck_task"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "output.log")
    
    with open(log_path, "w") as f:
        f.write(f"Ticket ID: {ticket_id}\n")
        f.write(f"Comment ID: {comment_id}\n")
        
    print(f"\nWritten results to {log_path}")

if __name__ == "__main__":
    main()
