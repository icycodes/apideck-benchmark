# Partition Open Tickets Across `in_progress` and `closed` via the Apideck Issue Tracking Unified API

## Background
Your engineering team uses Apideck Unify (`https://unify.apideck.com`) to drive ticket workflows across many backend issue trackers. For this task the consumer has already authorized **GitHub** (Service ID: `github`) as the Issue Tracking connector, and a single GitHub repository is exposed as the Apideck **Collection** identified by `APIDECK_ISSUE_TRACKING_COLLECTION_ID`.

Six `open` tickets have already been provisioned in that collection for this run. Their subjects all contain the marker `[PARTITION]` and the current `ZEALT_RUN_ID`. You must locate those six tickets via the Apideck unified API and split them into two halves by their unified `id`s.

The following environment variables are exported in the runtime:

- `APIDECK_APP_ID`
- `APIDECK_API_KEY`
- `APIDECK_CONSUMER_ID`
- `APIDECK_ISSUE_TRACKING_COLLECTION_ID`
- `ZEALT_RUN_ID` — a unique run id matching `zr-[a-z0-9]+`.

## Requirements
- Talk to the Apideck Issue Tracking Unified API (REST against `https://unify.apideck.com` or the `apideck-unify` SDK). Do **not** call the underlying GitHub REST/GraphQL API directly.
- Discover the six tickets in the collection whose `subject` contains both the literal substring `[PARTITION]` and the current `ZEALT_RUN_ID`. Use the List Tickets endpoint and follow `meta.cursors.next` if the result spans multiple pages.
- Sort those six tickets by their Apideck unified `id` in ascending lexicographic order to obtain positions 1..6.
- Transition the tickets at positions 1, 3, and 5 to status `in_progress`. Transition the tickets at positions 2, 4, and 6 to status `closed`. Use the Update Ticket endpoint for every transition.
- Do **not** create any additional ticket whose subject contains `[PARTITION]` and `ZEALT_RUN_ID`; the six pre-existing tickets must remain the only ones with that marker pair.
- Note: the GitHub connector does **not** support the unified `priority` field, so you **MUST NOT** send a `priority` value when updating any ticket.
- Write a log line for each ticket recording its final status. The log file format is described in *Acceptance Criteria*.

## Implementation Hints
- Every Apideck call needs the headers `Authorization: Bearer $APIDECK_API_KEY`, `x-apideck-app-id`, `x-apideck-consumer-id`, and `x-apideck-service-id: github`.
- List Tickets lives at `GET /issue-tracking/collections/{collection_id}/tickets` and supports `limit` (max 200) and cursor-based pagination via `meta.cursors.next`.
- Update Ticket lives at `PATCH /issue-tracking/collections/{collection_id}/tickets/{ticket_id}`. Apideck's unified `status` values are `open`, `in_progress`, and `closed`.
- The Python SDK exposes these as `apideck.issue_tracking.tickets.list(...)` and `apideck.issue_tracking.tickets.update(...)`.
- Refer to the Apideck docs at <https://developers.apideck.com/apis/issue-tracking/reference> and the [List Tickets](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsAll.md) and [Update Ticket](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsUpdate.md) pages.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the script actually runs against the live Apideck Unify API and the status transitions are visible through the Apideck Issue Tracking endpoints.
- Log file: /home/user/apideck_task/output.log
- The log file must contain exactly six lines, each in the format `Ticket <ticket_id>: <status>`, where `<ticket_id>` is the Apideck unified id of one of the six pre-existing `[PARTITION]` tickets and `<status>` is its final status (`in_progress` or `closed`).
- Exactly three of the lines must end with `in_progress` and exactly three must end with `closed`.
- When the six tickets are sorted by `<ticket_id>` ascending, positions 1, 3, 5 must be `in_progress` and positions 2, 4, 6 must be `closed`.
- `${ZEALT_RUN_ID}` must be read from the `ZEALT_RUN_ID` environment variable at runtime.

