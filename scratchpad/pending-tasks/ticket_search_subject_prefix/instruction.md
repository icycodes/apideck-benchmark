# Ticket Search by Subject Prefix

## Background
You are working with the ApiDeck Issue Tracking unified API connected to GitHub. You need to seed the configured collection with tickets that share two well-known subject prefixes so a downstream search workflow can locate them.

## Requirements
- Create 6 tickets in the collection identified by the `APIDECK_ISSUE_TRACKING_COLLECTION_ID` environment variable.
- Exactly 4 tickets must have a subject that starts with `SEARCH-MATCH-${ZEALT_RUN_ID}-`.
- Exactly 2 tickets must have a subject that starts with `SEARCH-OTHER-${ZEALT_RUN_ID}-`.
- Record the resulting ticket ids in a JSON log file so the verifier can reconcile them with what the API returns.

## Implementation Hints
- Use the ApiDeck Issue Tracking API with `service_id=github` and the standard ApiDeck headers (`Authorization`, `x-apideck-app-id`, `x-apideck-consumer-id`, `x-apideck-service-id`).
- Read all secrets from the environment (`APIDECK_API_KEY`, `APIDECK_APP_ID`, `APIDECK_CONSUMER_ID`, `APIDECK_ISSUE_TRACKING_COLLECTION_ID`, `ZEALT_RUN_ID`).
- The Issue Tracking Create Ticket endpoint is `POST /issue-tracking/collections/{collection_id}/tickets`.
- The GitHub connector does not honor every field — keep payloads minimal (subject is required).
- Capture the `id` returned by every create call; you will need to write them to the output log.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real ApiDeck calls are executed and the log artifact exists.
- Log file: /home/user/apideck_task/output.log
- The log file must contain a single JSON object with this exact shape:
  ```json
  {
    "matching_ids": ["<id>", "<id>", "<id>", "<id>"],
    "other_ids": ["<id>", "<id>"]
  }
  ```
- `matching_ids` must list the ids of the 4 tickets whose subject starts with `SEARCH-MATCH-${ZEALT_RUN_ID}-` (read from `ZEALT_RUN_ID`).
- `other_ids` must list the ids of the 2 tickets whose subject starts with `SEARCH-OTHER-${ZEALT_RUN_ID}-`.
- The two id sets must be disjoint and must each match the set of ids the verifier retrieves from ApiDeck by paginating List Tickets and filtering subject prefixes client-side.

