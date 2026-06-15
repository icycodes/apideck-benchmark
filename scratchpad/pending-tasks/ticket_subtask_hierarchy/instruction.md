# Build a Parent/Child Ticket Hierarchy with ApiDeck Issue Tracking

## Background
You are working with the ApiDeck Unified Issue Tracking API (connected to a GitHub repository). A product team needs to model a small feature breakdown as a hierarchy of tickets: a single parent epic with exactly three child sub-tasks that point back to it via `parent_id`.

## Requirements
- Use the ApiDeck Issue Tracking API to create the tickets in the pre-configured collection.
- Create exactly **one parent ticket** (no `parent_id`).
- Create exactly **three child tickets**, each with `parent_id` set to the parent ticket's returned `id`.
- Every ticket's `subject` must contain the value of the `ZEALT_RUN_ID` environment variable so concurrent runs do not collide.
- All four tickets (parent + children) must share a common subject prefix that you choose; the prefix must itself contain `ZEALT_RUN_ID`.
- After creating all tickets, write the resulting identifiers to a log artifact so the verifier can rediscover the hierarchy.

## Implementation Hints
- Read `APIDECK_APP_ID`, `APIDECK_API_KEY`, `APIDECK_CONSUMER_ID`, `APIDECK_ISSUE_TRACKING_COLLECTION_ID`, and `ZEALT_RUN_ID` from the environment.
- The connected service id for Issue Tracking is `github`; remember to send the `x-apideck-service-id` header.
- The GitHub connector does not support `priority`, so omit it.
- Refer to the ApiDeck Issue Tracking reference (Create Ticket, List Tickets, Get Ticket) to confirm request/response shapes and the `parent_id` field.
- You may use the `apideck-unify` Python SDK or plain HTTP; either is acceptable.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real ticket creation calls are executed against the live ApiDeck API and the log artifact exists.
- Log file: /home/user/apideck_task/output.log
- The log file must contain a single line that begins with `SUBJECT_PREFIX: ` followed by the common prefix you chose. The prefix MUST contain the value of `ZEALT_RUN_ID`.
- The log file must contain a single line that begins with `PARENT_ID: ` followed by the id returned by the API for the parent ticket.
- The log file must contain a single line that begins with `CHILD_IDS: ` followed by exactly three child ticket ids separated by commas (no spaces required).
- In the configured collection (`APIDECK_ISSUE_TRACKING_COLLECTION_ID`):
  - Exactly 1 ticket whose `subject` starts with the announced prefix and whose `parent_id` is empty/null.
  - Exactly 3 tickets whose `subject` starts with the announced prefix and whose `parent_id` equals the parent ticket's id.
  - Every such ticket's `subject` contains the value of `ZEALT_RUN_ID`.

