# Apply Resolved Tags To A New Ticket

## Background
You are integrating an internal triage tool with ApiDeck's Issue Tracking Unified API. The platform's GitHub connector is already configured. Your task is to discover which tags are currently available in the configured collection, select a subset by name convention, and create a single ticket that has exactly those tags attached.

## Requirements
- Resolve all tags whose `name` starts with the prefix `bench-` in the configured collection by listing tags through the ApiDeck Issue Tracking API. Do **NOT** hardcode tag ids.
- Create exactly one ticket in the same collection that includes the marker `[TAGS-APPLY]` and the current `ZEALT_RUN_ID` in its subject, and attach every resolved tag id to that ticket via the `tags[]` field on the create call.

## Implementation Hints
- Use the ApiDeck Issue Tracking API at `https://unify.apideck.com` with service id `github` and the collection id from `APIDECK_ISSUE_TRACKING_COLLECTION_ID`.
- The List Tags endpoint exposes each tag with a stable `id` and a human-readable `name`; filter on `name` client-side.
- The Create Ticket endpoint accepts a `tags` array where each item is an object with an `id` field.
- Read `ZEALT_RUN_ID` from the environment and place it in the ticket subject so concurrent runs do not collide.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real ticket creation action is executed and the log artifact exists.
- Log file: /home/user/apideck_task/output.log
- The ticket subject must contain both the literal marker `[TAGS-APPLY]` and the value of `ZEALT_RUN_ID`.
- Exactly one such ticket must exist in the configured collection at verification time.
- The set of tag ids attached to that ticket must equal the set of tag ids whose `name` starts with `bench-` as returned by the List Tags endpoint at verification time.
- The log file must contain a line in the format `Ticket ID: <ticket_id>`.

