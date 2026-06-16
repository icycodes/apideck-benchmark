# Cross-API Ticket / File Summary

Using Apideck Unify, perform these two side effects in the connected services for the current `ZEALT_RUN_ID`:

1. Upload exactly three small text files at the OneDrive drive root (service id `onedrive`), named (case-sensitive):
   - `REPORT-${ZEALT_RUN_ID}-A.txt`
   - `REPORT-${ZEALT_RUN_ID}-B.txt`
   - `REPORT-${ZEALT_RUN_ID}-C.txt`
2. Create exactly one Issue Tracking ticket (service id `github`, collection `APIDECK_ISSUE_TRACKING_COLLECTION_ID`) whose `subject` contains both `ZEALT_RUN_ID` and the literal marker `[FILE-INDEX]`, and whose `description` is the newline-joined list of those three uploaded files' Apideck file ids, sorted ascending. The description MUST contain only those three id lines and nothing else.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- The real Apideck side effects must be executed (no mocking).
- After completion, the OneDrive drive root contains exactly three files whose names equal `REPORT-${ZEALT_RUN_ID}-A.txt`, `REPORT-${ZEALT_RUN_ID}-B.txt`, `REPORT-${ZEALT_RUN_ID}-C.txt`.
- The Issue Tracking collection contains exactly one ticket whose `subject` includes both the literal substring `[FILE-INDEX]` and `${ZEALT_RUN_ID}`.
- That ticket's `description`, split by `\n` with empty lines discarded and surrounding whitespace stripped, equals the ascending-sorted list of the three uploaded files' Apideck `id` values.

