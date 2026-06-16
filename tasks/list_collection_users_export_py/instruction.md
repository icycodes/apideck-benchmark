# Export Issue Tracking Collection Users with Apideck Python SDK

## Background
Apideck Unified Issue Tracking exposes a `Users` resource scoped to a collection (e.g., a GitHub repository). These users are typically used to resolve assignee IDs before creating tickets. In this task you will use the official Apideck Python SDK (`apideck-unify`) to enumerate every user in the configured collection and persist them to a JSON artifact for downstream tooling.

The Issue Tracking connector is preconfigured to GitHub (service id `github`). The collection ID is provided via the `APIDECK_ISSUE_TRACKING_COLLECTION_ID` environment variable.

## Requirements
- Use the Apideck Python SDK to list every user in the configured Issue Tracking collection.
- Traverse cursor-based pagination so that ALL pages are collected, not just the first 20 results.
- Write the collected users to a JSON file inside the project directory.
- Write a log line capturing the total user count.

## Implementation Hints
- Install and use the `apideck-unify` Python SDK. The SDK exposes the Users endpoint as `apideck.issue_tracking.collection_users.list(...)`.
- The connector requires `service_id="github"` because multiple Unified APIs are enabled for the consumer.
- The SDK returns a pageable response object; call `.next()` to advance through cursor pagination until it returns `None`.
- Read all credentials from environment variables (`APIDECK_API_KEY`, `APIDECK_APP_ID`, `APIDECK_CONSUMER_ID`, `APIDECK_ISSUE_TRACKING_COLLECTION_ID`).

## Acceptance Criteria
- Project path: /home/user/myproject
- Ensure the script is executed and the artifacts exist.
- Log file: /home/user/myproject/output.log
  - The log file must contain a line in the format: `User count: <count>` where `<count>` is the integer number of users collected.
- Generated artifact: /home/user/myproject/users.json
  - The file must contain a single JSON object with the following shape:

    ```json
    {
      "collection_id": "<the configured collection id>",
      "service_id": "github",
      "users": [
        {
          "id": "<user id>",
          "name": "<full name or null>",
          "first_name": "<first name or null>",
          "last_name": "<last name or null>",
          "email": "<email or null>"
        }
      ]
    }
    ```
  - The `users` array must contain every user returned across all pages by the Apideck Issue Tracking List Users endpoint for the configured collection and `service_id=github`.
  - Every user object's `id` value must be a non-empty string.

