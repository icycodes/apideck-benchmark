# Reschedule a Ticket's Due Date via ApiDeck Issue Tracking

## Background
You are working with the ApiDeck Unified Issue Tracking API connected to GitHub. A product manager wants to track a release task in the configured issue-tracking collection. The task is initially scheduled for one date, but the release is later pushed back. You must create the ticket with the original due date, then update (PATCH) the ticket to the new due date.

## Requirements
- Use the ApiDeck Issue Tracking API (service id `github`) against the collection identified by the `APIDECK_ISSUE_TRACKING_COLLECTION_ID` environment variable.
- Create exactly ONE ticket whose `subject` includes both the current `ZEALT_RUN_ID` value AND the marker `[DUE-DATE]`.
- Create the ticket with an initial `due_date` of `2026-09-15T00:00:00.000Z`.
- After the ticket has been successfully created, reschedule it by issuing a PATCH that changes `due_date` to `2026-10-22T00:00:00.000Z`.
- Do NOT create any additional tickets carrying the `[DUE-DATE]` marker during the run.

## Implementation Hints
- Authenticate with the standard ApiDeck headers (`Authorization`, `x-apideck-app-id`, `x-apideck-consumer-id`, `x-apideck-service-id`).
- The unified Ticket schema represents `due_date` as an ISO 8601 `date-time` string.
- After PATCH, you may want to GET the ticket to confirm the rescheduled value before exiting.
- Avoid setting `priority` since the GitHub connector does not support it.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real ApiDeck API calls are executed against the live collection (no mocks).
- Log file: /home/user/apideck_task/output.log
- Across the configured issue-tracking collection, exactly ONE ticket must exist whose `subject` contains BOTH the current `ZEALT_RUN_ID` value AND the substring `[DUE-DATE]`.
- That ticket's `due_date` field, when parsed as an ISO 8601 instant, must equal `2026-10-22T00:00:00.000Z`.
- The log file must contain a line in the format: `Ticket ID: <ticket_id>` identifying the rescheduled ticket.

