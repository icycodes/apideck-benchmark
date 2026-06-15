# Add Twelve Comments and Paginate Them

## Background
A single ticket has been pre-created for you in the configured Issue Tracking collection (its `subject` contains the current `ZEALT_RUN_ID`). Your job is to use the ApiDeck Issue Tracking unified API to bulk-add twelve comments to that ticket, then list them back using cursor pagination.

## Requirements
- Locate the pre-existing ticket whose `subject` contains the current `ZEALT_RUN_ID` inside the collection identified by `APIDECK_ISSUE_TRACKING_COLLECTION_ID`.
- Add EXACTLY 12 comments to that ticket. Each comment's `body` must equal `COMMENT-{ZEALT_RUN_ID}-N` for N from 1 to 12.
- After all comments are created, list comments using cursor pagination with a small `limit` (so that several pages are required) and write a single log line per page to the output log.

## Implementation Hints
- Use the ApiDeck Issue Tracking unified API at `https://unify.apideck.com` with the GitHub service (`x-apideck-service-id: github`).
- Use the Issue Tracking Create Comment endpoint to add comments, and the List Comments endpoint with `cursor` and `limit` query parameters to paginate.
- Read all required configuration (`APIDECK_API_KEY`, `APIDECK_APP_ID`, `APIDECK_CONSUMER_ID`, `APIDECK_ISSUE_TRACKING_COLLECTION_ID`, `ZEALT_RUN_ID`) from environment variables.
- The Python SDK (`apideck-unify`) or raw HTTP both work; the verifier will only inspect side effects on the ticket.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the script is executed and the artifacts exist.
- Log file: /home/user/apideck_task/output.log
- The target ticket (subject contains `ZEALT_RUN_ID`) inside collection `APIDECK_ISSUE_TRACKING_COLLECTION_ID` must end up with exactly 12 comments whose bodies are `COMMENT-${ZEALT_RUN_ID}-1` through `COMMENT-${ZEALT_RUN_ID}-12` (each appearing exactly once).
- The log file must contain at least one line for each page fetched while paginating using the List Comments endpoint with `cursor` and a `limit` strictly less than 12 (so multiple pages are required). Each such line must be in the format: `PAGE <n> items=<count>` where `<n>` is the 1-based page index and `<count>` is the number of comments returned on that page.
- Comment ordering is not enforced.

