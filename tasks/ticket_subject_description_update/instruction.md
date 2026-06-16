# Apideck Issue Tracking: Ticket Subject & Description Update Workflow

## Background
You are working with the Apideck Unified Issue Tracking API connected to GitHub (service id `github`). Your job is to drive a small ticket-revision workflow: create a single ticket inside the configured collection with an initial subject and description, then update both fields via the unified PATCH endpoint, and finally persist the resulting ticket identifier for auditing.

## Requirements
- Create exactly one ticket inside the collection identified by the `APIDECK_ISSUE_TRACKING_COLLECTION_ID` environment variable.
- The initial subject must contain the literal marker `[UPDATE-V1]` together with the current `ZEALT_RUN_ID` value.
- After creation, update the ticket through the official unified Update Ticket endpoint so that the subject contains the literal marker `[UPDATE-V2]` together with the current `ZEALT_RUN_ID` value, and the description contains the literal string `Revised draft v2`.
- Record the resulting ticket identifier to a log file so the workflow is auditable.

## Implementation Hints
- Read all credentials, the collection id, and `ZEALT_RUN_ID` from environment variables before issuing any request.
- Apideck Unified APIs require `Authorization: Bearer <APIDECK_API_KEY>`, `x-apideck-app-id`, `x-apideck-consumer-id`, and `x-apideck-service-id: github` on every call.
- Use `POST /issue-tracking/collections/{collection_id}/tickets` to create the ticket and `PATCH /issue-tracking/collections/{collection_id}/tickets/{ticket_id}` to update it. Do not work around these endpoints with `pass_through` rewrites.
- The PATCH endpoint accepts `subject` and `description` in the request body; you must also include the ticket `id` in the body as required by the Apideck schema.
- Note that GitHub does not honor every unified field (for example `priority`). Stick to `subject` and `description` for this workflow.
- The List Tickets endpoint is cursor-paginated through `meta.cursors.next`; you may need to follow the cursor to verify the final state.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the script is executed and the artifacts exist.
- Log file: /home/user/apideck_task/output.log
- The log file must contain a line of the form `Ticket ID: <ticket_id>` for the ticket created by this run.
- After the workflow finishes, exactly one ticket exists in the configured collection whose subject contains both `[UPDATE-V2]` and the current `ZEALT_RUN_ID` value.
- No ticket in the configured collection has a subject that contains both `[UPDATE-V1]` and the current `ZEALT_RUN_ID` value.
- The ticket identified in the log has a description that contains the substring `Revised draft v2`.

