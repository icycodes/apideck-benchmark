# Bulk Close Tickets For The Current Run

## Background
Your team uses Apideck's Issue Tracking unified API (currently connected to GitHub) to manage support tickets. A scheduled job has just opened a batch of tickets in the shared collection for the current run. Your job is to close every ticket that belongs to this run, without touching anyone else's tickets.

## Requirements
- Sweep through the configured Issue Tracking collection and locate every ticket whose subject contains the current `ZEALT_RUN_ID`.
- Transition each of those tickets from `open` to `closed`.
- Leave all other tickets in the collection untouched.
- Do not create any new tickets in the collection.

## Implementation Hints
- Read all required configuration from the environment: `APIDECK_APP_ID`, `APIDECK_API_KEY`, `APIDECK_CONSUMER_ID`, `APIDECK_ISSUE_TRACKING_COLLECTION_ID`, `ZEALT_RUN_ID`.
- Use the Apideck unified `Issue Tracking` API at `https://unify.apideck.com` with service id `github` (set the `x-apideck-service-id: github` header).
- Listing tickets uses cursor pagination; follow `meta.cursors.next` until exhausted to ensure you do not miss any matching ticket.
- Updating a ticket's status uses `PATCH /issue-tracking/collections/{collection_id}/tickets/{ticket_id}` with a JSON body that includes `status: "closed"`.
- Write a short summary log to `/home/user/apideck_task/output.log` describing the matching ticket ids that you closed.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the script is executed and the artifacts exist.
- Log file: /home/user/apideck_task/output.log
- After your run, every ticket in collection `APIDECK_ISSUE_TRACKING_COLLECTION_ID` whose `subject` contains `ZEALT_RUN_ID` must have `status` equal to `closed` when fetched via the Apideck Issue Tracking API.
- The total number of tickets in that collection whose `subject` contains `ZEALT_RUN_ID` must remain exactly 5 (i.e., you must not create new run-scoped tickets).
- Tickets whose `subject` does not contain `ZEALT_RUN_ID` must not be modified.
- The log file must contain a line in the format `Closed ticket ids: <comma_separated_ids>` listing the ticket ids that were transitioned to `closed`.

