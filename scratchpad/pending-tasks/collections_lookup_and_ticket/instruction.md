# Collection Lookup and Ticket Creation

## Background
Use the ApiDeck Issue Tracking unified API (GitHub connector) to look up a specific collection and create a ticket whose subject embeds the collection's discovered name.

## Requirements
- Discover the collection identified by `APIDECK_ISSUE_TRACKING_COLLECTION_ID` and extract its canonical `name`.
- Create exactly one ticket in that collection whose subject embeds the discovered name and the current `ZEALT_RUN_ID`.
- Record the discovered name and the created ticket's id in a JSON log file.

## Implementation Hints
- All ApiDeck unified requests need `Authorization: Bearer <APIDECK_API_KEY>`, `x-apideck-app-id`, `x-apideck-consumer-id`, and `x-apideck-service-id: github`.
- The `name` field is part of the unified Collection schema returned by `GET /issue-tracking/collections` and `GET /issue-tracking/collections/{collection_id}`.
- Ticket creation: `POST /issue-tracking/collections/{collection_id}/tickets`.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real ApiDeck calls are executed and the artifacts exist.
- Log file: /home/user/apideck_task/output.log
- The log file must contain a single JSON object with exactly these fields:
  - `collection_name` (string): the `name` returned by ApiDeck for the collection whose id equals `APIDECK_ISSUE_TRACKING_COLLECTION_ID`.
  - `ticket_id` (string): the id of the ticket created in that collection.
- Exactly one ticket must exist in the configured collection whose subject equals `COLLNAME-${ZEALT_RUN_ID}-<collection_name>`, where `<collection_name>` is the exact `name` reported by ApiDeck.
- The `ticket_id` in the log must match the id of that ticket.

