import os
import json
from apideck_unify import Apideck
from apideck_unify.types import UNSET

def get_val(val):
    if val == UNSET or val is None:
        return None
    return val

def main():
    # Read environment variables
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")

    if not all([api_key, app_id, consumer_id, collection_id]):
        print("Error: Missing one or more required environment variables.")
        print(f"APIDECK_API_KEY present: {bool(api_key)}")
        print(f"APIDECK_APP_ID: {app_id}")
        print(f"APIDECK_CONSUMER_ID: {consumer_id}")
        print(f"APIDECK_ISSUE_TRACKING_COLLECTION_ID: {collection_id}")
        return

    # Initialize Apideck client
    sdk = Apideck(
        api_key=api_key,
        consumer_id=consumer_id,
        app_id=app_id
    )

    all_users = []
    
    # Fetch first page of users
    print(f"Fetching users for collection: {collection_id}")
    response = sdk.issue_tracking.collection_users.list(
        collection_id=collection_id,
        service_id="github"
    )

    current_page = response
    page_count = 0
    while current_page is not None:
        page_count += 1
        if current_page.get_collection_users_response and current_page.get_collection_users_response.data:
            page_users = current_page.get_collection_users_response.data
            print(f"Page {page_count}: received {len(page_users)} users")
            for user in page_users:
                # Map user object to required shape
                user_id = get_val(user.id)
                if not isinstance(user_id, str) or not user_id.strip():
                    # Skip or log warning for users without a non-empty string ID
                    print(f"Warning: Skipping user with invalid ID: {user_id}")
                    continue
                
                mapped_user = {
                    "id": user_id,
                    "name": get_val(user.name),
                    "first_name": get_val(user.first_name),
                    "last_name": get_val(user.last_name),
                    "email": get_val(user.email)
                }
                all_users.append(mapped_user)
        else:
            print(f"Page {page_count}: no users found in response")
            
        current_page = current_page.next()

    # Log total user count to output.log
    log_path = "/home/user/myproject/output.log"
    user_count = len(all_users)
    print(f"Total users collected: {user_count}")
    
    with open(log_path, "w") as f:
        f.write(f"User count: {user_count}\n")
    print(f"Wrote log to {log_path}")

    # Write users to users.json
    artifact_path = "/home/user/myproject/users.json"
    output_data = {
        "collection_id": collection_id,
        "service_id": "github",
        "users": all_users
    }
    
    with open(artifact_path, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"Wrote artifact to {artifact_path}")

if __name__ == "__main__":
    main()
