import os
import json
import urllib.request
import urllib.error

def main():
    app_id = os.environ.get("APIDECK_APP_ID")
    api_key = os.environ.get("APIDECK_API_KEY")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "github",
        "Content-Type": "application/json"
    }

    base_url = "https://unify.apideck.com"

    # Read ticket_id and comment_id from output.log
    ticket_id = None
    comment_id = None
    with open("/home/user/apideck_task/output.log", "r") as f:
        for line in f:
            if line.startswith("Ticket ID:"):
                ticket_id = line.split(":", 1)[1].strip()
            elif line.startswith("Comment ID:"):
                comment_id = line.split(":", 1)[1].strip()

    print(f"Verifying Ticket ID: {ticket_id}")
    print(f"Verifying Comment ID: {comment_id}")

    # 1. GET /issue-tracking/collections/{collection_id}/tickets/{ticket_id}
    ticket_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}"
    req = urllib.request.Request(ticket_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            print("\nFetched Ticket:")
            print(json.dumps(res_data, indent=2))
            
            ticket = res_data.get("data", {})
            assert ticket.get("id") == ticket_id, "Ticket ID mismatch!"
            assert ticket.get("subject") == f"[triage] login button broken {run_id}", f"Subject mismatch! Got: {ticket.get('subject')}"
            assert ticket.get("status") == "closed", f"Status is not closed! Got: {ticket.get('status')}"
            print("Ticket validation passed!")
    except Exception as e:
        print(f"Ticket validation failed: {e}")
        return

    # 2. GET /issue-tracking/collections/{collection_id}/tickets/{ticket_id}/comments
    comment_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}/comments"
    req = urllib.request.Request(comment_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            print("\nFetched Comments:")
            print(json.dumps(res_data, indent=2))
            
            comments = res_data.get("data", [])
            comment_found = False
            for c in comments:
                if c.get("id") == comment_id:
                    comment_found = True
                    assert c.get("body") == "Reproduced and assigned to backend squad. Closing as duplicate of internal report.", f"Comment body mismatch! Got: {c.get('body')}"
            assert comment_found, f"Comment ID {comment_id} not found in comments list!"
            print("Comment validation passed!")
    except Exception as e:
        print(f"Comment validation failed: {e}")
        return

    print("\nAll verifications passed perfectly!")

if __name__ == "__main__":
    main()
