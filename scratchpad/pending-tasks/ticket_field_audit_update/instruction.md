# ApiDeck Issue Tracking: Field Audit Update

## Background
Your team is auditing how ApiDeck's unified Issue Tracking API propagates field updates to GitHub. You must create a single audit ticket, then update its `subject` and `description` through a deterministic sequence of PATCH calls, recording the response status of every PATCH for later inspection.

## Requirements
- Use the ApiDeck unified Issue Tracking API against the preconfigured GitHub collection (`APIDECK_ISSUE_TRACKING_COLLECTION_ID`, service id `github`).
- Create exactly ONE ticket whose initial `subject` contains both the marker `[FIELD-AUDIT]` and the current `ZEALT_RUN_ID`.
- After creation, perform exactly TWO sequential PATCH updates to the ticket's `subject` (first to an intermediate value, then to the final value).
- After creation, perform exactly TWO sequential PATCH updates to the ticket's `description` (first to an intermediate value, then to the final value).
- Record every PATCH response status code and the values sent in a JSON artifact log.

## Implementation Hints
- Read `ZEALT_RUN_ID`, `APIDECK_APP_ID`, `APIDECK_API_KEY`, `APIDECK_CONSUMER_ID`, and `APIDECK_ISSUE_TRACKING_COLLECTION_ID` from the environment.
- Send `x-apideck-service-id: github` on every Issue Tracking request.
- Each PATCH must target the ticket id returned by the Create Ticket call and must be performed sequentially (do not batch).
- Use the standard `requests` HTTP client (already installed) for direct REST calls if you prefer not to use the SDK.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real ApiDeck calls are executed and the artifact log exists.
- Log file: /home/user/apideck_task/output.log
- The log file must be valid JSON with this shape:
  ```json
  {
    "ticket_id": "<ticket id returned by ApiDeck>",
    "subjects": ["<initial subject>", "<intermediate subject>", "<final subject>"],
    "descriptions": ["<initial description>", "<intermediate description>", "<final description>"],
    "patch_statuses": {
      "subject": [<int>, <int>],
      "description": [<int>, <int>]
    }
  }
  ```
- Exactly ONE ticket in the collection has a subject containing both `[FIELD-AUDIT]` and the `ZEALT_RUN_ID` value.
- The ticket's FINAL `subject` (as returned by ApiDeck Get Ticket) equals exactly: `FINAL-SUBJECT-${ZEALT_RUN_ID}-[FIELD-AUDIT]`.
- The ticket's FINAL `description` (as returned by ApiDeck Get Ticket) equals exactly: `FINAL-DESCRIPTION-${ZEALT_RUN_ID}`.

