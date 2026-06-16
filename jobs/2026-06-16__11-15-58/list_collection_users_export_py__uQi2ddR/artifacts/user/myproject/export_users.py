#!/usr/bin/env python3
"""Export Issue Tracking Collection Users using the Apideck Unify SDK."""

import json
import os
import sys

from apideck_unify import Apideck
from apideck_unify.types import UNSET

def main():
    # Read configuration from environment variables
    api_key = os.environ["APIDECK_API_KEY"]
    app_id = os.environ["APIDECK_APP_ID"]
    consumer_id = os.environ["APIDECK_CONSUMER_ID"]
    collection_id = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]

    # Initialize the Apideck client
    apideck = Apideck(
        api_key=api_key,
        app_id=app_id,
        consumer_id=consumer_id,
    )

    all_users = []
    service_id = "github"

    # First call - list users with service_id filter
    response = apideck.issue_tracking.collection_users.list(
        collection_id=collection_id,
        service_id=service_id,
    )

    while True:
        # Extract data from the response
        inner = response.get_collection_users_response
        if inner is None:
            break

        for user in inner.data:
            user_obj = {
                "id": user.id if not isinstance(user.id, type(UNSET)) and user.id is not None else None,
                "name": user.name if not isinstance(user.name, type(UNSET)) and user.name is not None else None,
                "first_name": user.first_name if not isinstance(user.first_name, type(UNSET)) and user.first_name is not None else None,
                "last_name": user.last_name if not isinstance(user.last_name, type(UNSET)) and user.last_name is not None else None,
                "email": user.email if not isinstance(user.email, type(UNSET)) and user.email is not None else None,
            }
            all_users.append(user_obj)

        # Advance to the next page using the .next() callable
        response = response.next()
        if response is None:
            break

    # Build the output JSON
    output = {
        "collection_id": collection_id,
        "service_id": service_id,
        "users": all_users,
    }

    # Write users.json
    project_dir = "/home/user/myproject"
    users_path = os.path.join(project_dir, "users.json")
    with open(users_path, "w") as f:
        json.dump(output, f, indent=2)

    # Write output.log
    log_path = os.path.join(project_dir, "output.log")
    with open(log_path, "w") as f:
        f.write(f"User count: {len(all_users)}\n")

    print(f"Exported {len(all_users)} users to {users_path}")
    print(f"Log written to {log_path}")


if __name__ == "__main__":
    main()