# Triage and Close a Bug Ticket via the Apideck Issue Tracking Unified API

## Background
Your engineering team uses Apideck Unify to triage bug reports across multiple issue trackers through a single canonical REST surface. For this task, the consumer has already authorized **GitHub** (Service ID: `github`) as the Issue Tracking connector, and a single GitHub repository has been provisioned and exposed as an Apideck **Collection**.

You must drive a full triage lifecycle on a brand-new ticket through the Apideck Issue Tracking Unified API (`https://unify.apideck.com`): create a ticket, append an investigation comment to it, then transition it to a closed state and record everything for the verifier.

The following environment variables are already exported in the runtime:

- `APIDECK_APP_ID`
- `APIDECK_API_KEY`
- `APIDECK_CONSUMER_ID`
- `APIDECK_ISSUE_TRACKING_COLLECTION_ID` — the Apideck Collection ID that maps to the pre-provisioned GitHub repository. Use it as `collection_id` in every Issue Tracking request.
- `ZEALT_RUN_ID` — a unique run id matching `zr-[a-z0-9]+`. You **must** include it in the ticket subject so concurrent runs do not collide.

## Requirements
- Use the Apideck Issue Tracking Unified API (REST against `https://unify.apideck.com` or the official `apideck-unify` SDK). Do **not** call the underlying GitHub REST/GraphQL API directly.
- Create a single ticket in the collection identified by `APIDECK_ISSUE_TRACKING_COLLECTION_ID`. The ticket subject must be exactly `[triage] login button broken ${ZEALT_RUN_ID}` (substitute the run id at runtime). The ticket description must be exactly `Reported by user; affects Safari 17. Triaged via Apideck run ${ZEALT_RUN_ID}.`.
- The ticket must be created with `status` set to `open`.
- Add exactly one comment to the freshly created ticket. The comment `body` must be exactly `Reproduced and assigned to backend squad. Closing as duplicate of internal report.`.
- After the comment is created, transition the ticket to `status` `closed` using the Update Ticket endpoint.
- Capture the Apideck-returned identifiers and write them to the log file described below.
- Note: the GitHub connector does **not** support the unified `priority` field, so you **MUST NOT** send a `priority` value when creating or updating the ticket.

## Implementation Hints
- Every Apideck call needs the headers `Authorization: Bearer $APIDECK_API_KEY`, `x-apideck-app-id`, `x-apideck-consumer-id`, and `x-apideck-service-id: github`.
- The Create Ticket endpoint is `POST /issue-tracking/collections/{collection_id}/tickets`, Create Comment is `POST /issue-tracking/collections/{collection_id}/tickets/{ticket_id}/comments`, and Update Ticket is `PATCH /issue-tracking/collections/{collection_id}/tickets/{ticket_id}`.
- The Python SDK exposes these as `apideck.issue_tracking.tickets.create(...)`, `apideck.issue_tracking.comments.create(...)`, and `apideck.issue_tracking.tickets.update(...)`. Each response wraps the new resource id under `data.id`.
- Apideck's unified `status` values are `open`, `in_progress`, and `closed`. The ticket must end in the `closed` state.
- Refer to the Apideck docs at <https://developers.apideck.com/apis/issue-tracking/reference> and the [Create Ticket](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsAdd.md), [Create Comment](https://developers.apideck.com/md/apis/issue-tracking/reference/comments/collectionTicketCommentsAdd.md), and [Update Ticket](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsUpdate.md) pages.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the script is actually executed against the live Apideck Unify API and the GitHub side effects (ticket creation, comment creation, status update) are visible through the Apideck Issue Tracking endpoints.
- Log file: /home/user/apideck_task/output.log
- The log file must contain the following two lines (each on its own line, in any order):
  - `Ticket ID: <ticket_id>`
  - `Comment ID: <comment_id>`
  Where `<ticket_id>` and `<comment_id>` are the Apideck unified IDs returned by the Create Ticket and Create Comment endpoints respectively.
- A ticket whose `id` equals `<ticket_id>` must exist in the collection identified by `APIDECK_ISSUE_TRACKING_COLLECTION_ID` when fetched via `GET /issue-tracking/collections/{collection_id}/tickets/{ticket_id}` with the headers shown in *Implementation Hints*.
- The ticket's `subject` must equal `[triage] login button broken ${ZEALT_RUN_ID}` (with `${ZEALT_RUN_ID}` read from the environment at runtime).
- The ticket's `status` must equal `closed` at the time of verification.
- A comment whose `id` equals `<comment_id>` must be returned by `GET /issue-tracking/collections/{collection_id}/tickets/{ticket_id}/comments`, and its `body` must equal `Reproduced and assigned to backend squad. Closing as duplicate of internal report.`.
- `${ZEALT_RUN_ID}` must be read from the `ZEALT_RUN_ID` environment variable at runtime.

