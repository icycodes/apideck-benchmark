#!/usr/bin/env python3
"""Export all users from an Apideck Issue Tracking collection to a JSON artifact."""

import json
import os
import sys

from apideck_unify import Apideck


def main():
    # Read credentials from environment
    api_key = os.environ["APIDECK_API_KEY"]
    app_id = os.environ["APIDECK_APP_ID"]
    consumer_id = os.environ["APIDECK_CONSUMER_ID"]
    collection_id = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]
    service_id = "github"

    # Initialize the SDK
    sdk = Apideck(
        api_key=api_key,
        app_id=app_id,
        consumer_id=consumer_id,
    )

    all_users = []
    cursor = None

    while True:
        # Fetch a page of users
        resp = sdk.issue_tracking.collection_users.list(
            collection_id=collection_id,
            service_id=service_id,
            cursor=cursor,
            limit=200,  # fetch as many as allowed per page
        )

        gcur = resp.get_collection_users_response
        if gcur is not None and gcur.data is not None:
            for user in gcur.data:
                user_dict = user.model_dump()
                all_users.append({
                    "id": user_dict.get("id", ""),
                    "name": user_dict.get("name"),
                    "first_name": user_dict.get("first_name"),
                    "last_name": user_dict.get("last_name"),
                    "email": user_dict.get("email"),
                })

        # Advance to the next page; returns None when exhausted
        next_resp = resp.next()
        if next_resp is None:
            break

        # Extract the cursor for the next iteration
        next_gcur = next_resp.get_collection_users_response
        if next_gcur is not None and next_gcur.meta is not None and next_gcur.meta.cursors is not None:
            cursor = next_gcur.meta.cursors.next
        else:
            break

    # Build the output artifact
    artifact = {
        "collection_id": collection_id,
        "service_id": service_id,
        "users": all_users,
    }

    # Write users.json
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
    with open(output_path, "w") as f:
        json.dump(artifact, f, indent=2)

    # Write log line
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.log")
    with open(log_path, "w") as f:
        f.write(f"User count: {len(all_users)}\n")

    print(f"Exported {len(all_users)} users to {output_path}")
    print(f"Log written to {log_path}")


if __name__ == "__main__":
    main()
