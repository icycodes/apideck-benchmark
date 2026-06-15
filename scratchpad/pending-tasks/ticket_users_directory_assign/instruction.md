# Assign First Directory User to a New Ticket via Apideck Issue Tracking

## Background
You are integrating with Apideck's unified Issue Tracking API (connected to GitHub as the underlying provider). A new ticket needs to be opened in the preconfigured collection and assigned to a specific user from the collection's user directory. The assignee must be resolved dynamically from the Apideck Users endpoint; hard-coded user identifiers are not allowed.

## Requirements
- Discover the eligible assignee by calling the Apideck Users endpoint for the configured collection.
- Create a single ticket in the configured collection whose subject contains the marker `[USER-ASSIGN]` and the current `ZEALT_RUN_ID`.
- Assign that ticket to the user whose `id` is the smallest (lexicographic minimum) `id` returned by the Users endpoint.
- Persist evidence of the run to a local log file.

## Implementation Hints
- All Apideck calls require the `Authorization`, `x-apideck-app-id`, `x-apideck-consumer-id`, and `x-apideck-service-id` headers. The Issue Tracking connector uses service id `github`.
- Resolve the eligible assignee via `GET /issue-tracking/collections/{collection_id}/users` and pick the user with the lexicographically smallest `id`. Do not hardcode any user id.
- Create the ticket with `POST /issue-tracking/collections/{collection_id}/tickets`, supplying the resolved id as an element of `assignees` (the schema is `assignees: [{ "id": "<user_id>" }]`).
- Read configuration from the environment variables: `APIDECK_APP_ID`, `APIDECK_API_KEY`, `APIDECK_CONSUMER_ID`, `APIDECK_ISSUE_TRACKING_COLLECTION_ID`, and `ZEALT_RUN_ID`.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real Apideck API calls are executed and the log artifact exists.
- Log file: /home/user/apideck_task/output.log
- Exactly one ticket must exist in the configured collection whose subject contains both the marker `[USER-ASSIGN]` and the value of `ZEALT_RUN_ID`.
- That ticket's `assignees` array must contain exactly one entry, and its `id` must equal the lexicographically smallest `id` returned by the Users endpoint at verification time.
- The log file must contain a line in the format `Ticket ID: <ticket_id>` recording the id of the created ticket.

