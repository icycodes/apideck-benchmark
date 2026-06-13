# ApiDeck Research Plan

## 1. Library Overview

* **Description**: Apideck is a unified API platform that lets B2B SaaS apps integrate once and immediately ship integrations across 200+ third‑party services. Apideck normalizes messy, inconsistent vendor APIs (CRM, Accounting, HRIS, ATS, File Storage, E‑commerce, Issue Tracking, etc.) into a single canonical data model accessible at one base URL: `https://unify.apideck.com`. Auth, OAuth, schema mapping, pagination, webhooks, and rate‑limit handling are all unified across providers. Apideck runs in real‑time pass‑through mode (no data storage).
* **Ecosystem Role**: Sits between a customer‑facing SaaS backend and many third‑party SaaS providers (Jira, GitHub, Linear, Asana for issue tracking; Google Drive, Dropbox, Box, OneDrive, SharePoint for file storage). Apideck's **Vault** product manages per‑consumer OAuth connections, while the **Unified APIs** expose a single normalized REST surface. **Proxy API** is offered for raw downstream calls when something isn't unified.
* **Project Setup**:
  1. Create an account at [apideck.com/signup](https://www.apideck.com/signup) and choose an application + subdomain.
  2. In the [Configuration dashboard](https://platform.apideck.com/configuration), enable one or more **Unified APIs** (e.g., Issue Tracking, File Storage) and pick connectors.
  3. Copy your **App ID** and **API Key** from the [API Keys page](https://platform.apideck.com/configuration/api-keys).
  4. Create a **consumer** (typically your internal user ID) via a Vault session:
     ```bash
     curl -X POST https://unify.apideck.com/vault/sessions \
       -H "Authorization: Bearer $APIDECK_API_KEY" \
       -H "x-apideck-app-id: $APIDECK_APP_ID" \
       -H "x-apideck-consumer-id: $APIDECK_CONSUMER_ID" \
       -d '{"redirect_uri":"https://example.com/done"}'
     ```
  5. Open the Vault URL (Hosted Vault, Vault JS, React, or Vue), let the consumer authorize a connector (e.g., GitHub for Issue Tracking, OneDrive for File Storage), and then make calls.
  6. Install an SDK: `pip install apideck-unify` (Python) or `npm install @apideck/unify` (Node), or call REST directly. All requests require these headers:
     * `Authorization: Bearer <APIDECK_API_KEY>`
     * `x-apideck-app-id: <APIDECK_APP_ID>`
     * `x-apideck-consumer-id: <APIDECK_CONSUMER_ID>`
     * `x-apideck-service-id: <connector_id>` (e.g., `github`, `one-drive`) — required when multiple connectors are active in a Unified API.

## 2. Core Primitives & APIs

All endpoints below are under the base URL `https://unify.apideck.com` and share the headers listed above. (File **uploads/downloads** must hit `https://upload.apideck.com` instead — see Friction Points.)

### 2.1 Issue Tracking API

Docs: [Issue Tracking reference](https://developers.apideck.com/apis/issue-tracking/reference). The data model is **Collection → Ticket → Comment** with associated **Users** and **Tags**. A "Collection" is the unified concept for a Jira project, Linear team, GitHub repository, Asana project, etc.

#### Collections
Read‑only in the unified API. Used as the parent scope for tickets, users, and tags.

* `GET /issue-tracking/collections` — [List Collections](https://developers.apideck.com/md/apis/issue-tracking/reference/collections/collectionsAll.md)
* `GET /issue-tracking/collections/{collection_id}` — [Get Collection](https://developers.apideck.com/md/apis/issue-tracking/reference/collections/collectionsOne.md)

```python
from apideck_unify import Apideck

with Apideck(api_key=API_KEY, app_id=APP_ID, consumer_id=CONSUMER_ID) as apideck:
    collections = apideck.issue_tracking.collections.list(service_id="github")
    print([c.id for c in collections.get_collections_response.data])
```

#### Tickets
Full CRUD against a collection. Required field on create is `id` (unified identifier) plus `subject`/`description`/`type`/`priority`/`status`/`assignees`/`tags`/`due_date`.

* `GET /issue-tracking/collections/{collection_id}/tickets` — [List Tickets](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsAll.md) (supports `cursor`, `limit` 1–200, `filter`, `sort`, `fields`, `pass_through`).
* `POST /issue-tracking/collections/{collection_id}/tickets` — [Create Ticket](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsAdd.md). Body fields include `subject`, `description`, `type`, `status` (`open|in_progress|closed`), `priority` (`low|normal|high|urgent`), `assignees[]`, `tags[]`, `due_date`, `parent_id`.
* `GET /issue-tracking/collections/{collection_id}/tickets/{ticket_id}` — [Get Ticket](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsOne.md).
* `PATCH /issue-tracking/collections/{collection_id}/tickets/{ticket_id}` — [Update Ticket](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsUpdate.md).
* `DELETE /issue-tracking/collections/{collection_id}/tickets/{ticket_id}` — [Delete Ticket](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsDelete.md).

```bash
curl -X POST "https://unify.apideck.com/issue-tracking/collections/$COLLECTION_ID/tickets" \
  -H "Authorization: Bearer $APIDECK_API_KEY" \
  -H "x-apideck-app-id: $APIDECK_APP_ID" \
  -H "x-apideck-consumer-id: $APIDECK_CONSUMER_ID" \
  -H "x-apideck-service-id: github" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Login button broken",
    "description": "Reproduces on Safari 17",
    "priority": "high",
    "status": "open",
    "assignees": [{"id": "12345"}],
    "tags": [{"id": "bug"}]
  }'
```

#### Comments
Threaded against a ticket.

* `GET /.../tickets/{ticket_id}/comments` — [List Comments](https://developers.apideck.com/md/apis/issue-tracking/reference/comments/collectionTicketCommentsAll.md)
* `POST /.../tickets/{ticket_id}/comments` — [Create Comment](https://developers.apideck.com/md/apis/issue-tracking/reference/comments/collectionTicketCommentsAdd.md) (body field: `body`).
* `GET /.../tickets/{ticket_id}/comments/{id}` — Get Comment.
* `PATCH /.../tickets/{ticket_id}/comments/{id}` — Update Comment.
* `DELETE /.../tickets/{ticket_id}/comments/{id}` — Delete Comment.

#### Users & Tags (read‑only, scoped to a collection)
* `GET /.../collections/{collection_id}/users`, `GET /.../users/{id}` — [Users](https://developers.apideck.com/md/apis/issue-tracking/reference/users.md). Useful for resolving `assignees[].id` before creating tickets.
* `GET /.../collections/{collection_id}/tags` — [Tags](https://developers.apideck.com/md/apis/issue-tracking/reference/tags.md). Useful for resolving `tags[].id` before creating tickets.

### 2.2 File Storage API

Docs: [File Storage reference](https://developers.apideck.com/apis/file-storage/reference). Resources: **Drives → Folders → Files**, plus **Shared Links**, **Upload Sessions**, and **Drive Groups**.

#### Drives
* `GET /file-storage/drives` — [List Drives](https://developers.apideck.com/md/apis/file-storage/reference/drives/drivesAll.md)
* `POST /file-storage/drives` — Create Drive (not supported by OneDrive — see Integration note below).
* `GET /file-storage/drives/{id}` — Get Drive.
* `PATCH /file-storage/drives/{id}` — Update Drive.
* `DELETE /file-storage/drives/{id}` — Delete Drive.

#### Folders
* `POST /file-storage/folders` — [Create Folder](https://developers.apideck.com/md/apis/file-storage/reference/folders/foldersAdd.md). Required: `name`, `parent_folder_id` (use `"root"` for the drive root). Optional: `description`, `drive_id`.
* `GET /file-storage/folders/{id}` — Get Folder.
* `PATCH /file-storage/folders/{id}` — Rename or move Folder.
* `POST /file-storage/folders/{id}/copy` — Copy Folder.
* `DELETE /file-storage/folders/{id}` — Delete Folder.

#### Files
* `GET /file-storage/files` — [List Files](https://developers.apideck.com/md/apis/file-storage/reference/files/filesAll.md) (cursor pagination, `filter`, `sort`, `fields`). Each item exposes `name`, `type` (`file|folder|url`), `path`, `mime_type`, `size`, `parent_folders[]`, `owner`, timestamps.
* `POST /file-storage/files/search` — Search Files (body filters).
* `POST /file-storage/files` — [Upload file](https://developers.apideck.com/md/apis/file-storage/reference/files/filesUpload.md) (≤100 MB, raw binary body, metadata in `x-apideck-metadata` header, hosted at `https://upload.apideck.com`).
* `GET /file-storage/files/{id}` — Get File metadata.
* `PATCH /file-storage/files/{id}` — Rename or move File.
* `GET /file-storage/files/{id}/download` — Download File (binary stream).
* `GET /file-storage/files/{id}/export` — Export File (for proprietary formats like Google Docs).
* `DELETE /file-storage/files/{id}` — Delete File.

```bash
# Direct (<=100 MB) upload — note the upload.apideck.com host
curl -X POST "https://upload.apideck.com/file-storage/files" \
  -H "Authorization: Bearer $APIDECK_API_KEY" \
  -H "x-apideck-app-id: $APIDECK_APP_ID" \
  -H "x-apideck-consumer-id: $APIDECK_CONSUMER_ID" \
  -H "x-apideck-service-id: one-drive" \
  -H "Content-Type: text/plain" \
  -H 'x-apideck-metadata: {"name":"hello.txt","parent_folder_id":"root"}' \
  --data-binary @hello.txt
```

#### Upload Sessions (for files >100 MB)
[Guide](https://developers.apideck.com/guides/file-upload.md). Flow: `POST /upload-sessions` → `GET /upload-sessions/{id}` (to discover `part_size`) → `PUT /upload-sessions/{id}?part_number=N` (one PUT per part, starting at part 0) → `POST /upload-sessions/{id}/finish`.

#### Shared Links
* `GET /file-storage/shared-links`, `POST /file-storage/shared-links`, `GET /shared-links/{id}`, `PATCH /shared-links/{id}`, `DELETE /shared-links/{id}` — manage public/scoped sharing URLs for files & folders. See [Shared Links reference](https://developers.apideck.com/md/apis/file-storage/reference/shared-links.md).

#### Drive Groups
Read/write groups of drives (mostly relevant for SharePoint/Google Drive shared drives). See [Drive Groups reference](https://developers.apideck.com/md/apis/file-storage/reference/drive-groups.md).

```python
# Python SDK example — upload then list
from apideck_unify import Apideck

with Apideck(api_key=API_KEY, app_id=APP_ID, consumer_id=CONSUMER_ID) as apideck:
    apideck.file_storage.files.upload(
        service_id="one-drive",
        name="report.txt",
        parent_folder_id="root",
        file=b"hello world",
    )
    files = apideck.file_storage.files.list(service_id="one-drive")
```

## 3. Real-World Use Cases & Templates

* **Apideck samples index**: [developers.apideck.com/samples](https://developers.apideck.com/samples.md) — open‑source reference apps across Vault, file picker, accounting, etc.
* **File Picker sample**: A drop‑in React file browser/uploader backed by the File Storage API ([guide](https://developers.apideck.com/guides/file-picker.md)).
* **Common patterns**:
  * Sync engineering tickets from GitHub/Jira/Linear into an internal dashboard via Issue Tracking (Collections → Tickets → Comments).
  * Embed "Save to my cloud drive" / "Attach from my drive" buttons via File Storage and Shared Links.
  * Set up native or virtual **webhooks** ([guide](https://developers.apideck.com/guides/webhooks.md)) so the app reacts to ticket changes or new files in real time.
  * Use **Field Mapping** ([guide](https://developers.apideck.com/guides/field-mapping.md)) to surface connector‑specific fields back through the unified model.
  * Use **Unified Pass Through** ([guide](https://developers.apideck.com/guides/pass-through.md)) when a connector exposes parameters that aren't part of the unified schema.

## 4. Developer Friction Points

1. **Two different hosts: `unify.apideck.com` vs `upload.apideck.com`.** Direct uploads, upload sessions, and downloads of binary payloads must go through `https://upload.apideck.com` — easy to miss because the rest of the API lives on `unify.apideck.com`. See the [file upload guide](https://developers.apideck.com/guides/file-upload.md).
2. **File metadata travels in an HTTP header.** `x-apideck-metadata` must contain a JSON string with at least `name` and `parent_folder_id`. The request body must be the **raw binary** of the file, not multipart/form‑data. A common mistake is using `--form` with curl, which silently fails or returns 400/422.
3. **Conflict behavior on duplicate file names differs by connector.** Per the [file upload guide matrix](https://developers.apideck.com/guides/file-upload.md), Google Drive will create a new file with the same name (files are not unique by name), OneDrive/SharePoint replace, Dropbox autorenames, Box errors. Tests cannot assume a single "the previous file was overwritten" outcome.
4. **Collections cannot be created via the unified Issue Tracking API.** Only `GET` operations are exposed for Collections; teams must create the underlying Jira project / GitHub repo / Linear team via the provider UI (or the Proxy API) first, then use that ID as `collection_id` for ticket operations.
5. **Connectors require `x-apideck-service-id` once multiple are enabled** for the same Unified API, and many connectors expose a "Needs configuration" state after OAuth ([connection states guide](https://developers.apideck.com/guides/connection-states.md)). Forgetting the header or skipping configuration yields 422/404 responses that look like bugs in the unified API.
6. **Cursor pagination is opaque.** Responses include `meta.cursors.{previous,current,next}` and `links.{previous,current,next}`; you must use them rather than computing offsets. Default `limit` is 20, max 200 — see [Unified Rate Limits](https://developers.apideck.com/guides/unified-rate-limits.md).

## 5. Evaluation Ideas

* (Easy) Use the Issue Tracking API to list tickets in the preconfigured collection and assert the response shape.
* (Easy) Use the File Storage API to upload a small text file to the configured OneDrive drive root and verify it via `GET /file-storage/files`.
* (Medium) Create a ticket with a specified priority, assignees, and tags, then update its status and assert the change via `GET`.
* (Medium) Create a folder in OneDrive, upload a file into it, then create a shared link for that file and validate the link metadata.
* (Medium) Add a comment to an existing ticket, list comments, and ensure ordering/pagination work with cursor parameters.
* (Hard) Implement multipart upload using the Upload Sessions flow for a file larger than 100 MB, then download it back and compare hashes.
* (Hard) Synchronize a ticket lifecycle: create a ticket, attach a file from File Storage as a comment (via shared link), patch the ticket, and finally delete both — verifying side effects after each step.
* (Hard) Implement cursor‑based pagination across both Tickets and Files to collect all entries created in the current run (filtering by `ZEALT_RUN_ID` in name/subject) and reconcile counts.

## 6. Sources

1. [Apideck llms.txt](https://developers.apideck.com/llms.txt) — Curated index of all Apideck developer docs.
2. [Get Started](https://developers.apideck.com/get-started.md) — Account, API key, consumer, and Vault setup.
3. [Issue Tracking API reference](https://developers.apideck.com/apis/issue-tracking/reference.md) — Endpoint catalog for Collections, Tickets, Comments, Users, Tags.
4. [Create Ticket](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsAdd.md) — Request body and response schema for ticket creation.
5. [List Tickets](https://developers.apideck.com/md/apis/issue-tracking/reference/tickets/collectionTicketsAll.md) — Pagination, filter, sort parameters.
6. [Create Comment](https://developers.apideck.com/md/apis/issue-tracking/reference/comments/collectionTicketCommentsAdd.md) — Comment schema.
7. [File Storage API reference](https://developers.apideck.com/apis/file-storage/reference.md) — Endpoint catalog for Files, Folders, Shared Links, Upload Sessions, Drives, Drive Groups.
8. [Upload File](https://developers.apideck.com/md/apis/file-storage/reference/files/filesUpload.md) — Direct upload endpoint schema.
9. [List Files](https://developers.apideck.com/md/apis/file-storage/reference/files/filesAll.md) — File listing schema with fields, pagination, MIME types.
10. [Create Folder](https://developers.apideck.com/md/apis/file-storage/reference/folders/foldersAdd.md) — Folder creation request body.
11. [Uploading Files guide](https://developers.apideck.com/guides/file-upload.md) — Direct vs Upload Sessions flow, conflict behavior matrix.
12. [Python SDK](https://developers.apideck.com/sdks/python.md) — `apideck-unify` install and usage.
13. [Issue Tracking marketing page](https://www.apideck.com/issue-tracking-api) — Supported connectors (Jira, Linear, GitHub, Asana, …).
14. [File Storage marketing page](https://www.apideck.com/file-storage-api) — Supported connectors (Google Drive, Dropbox, Box, OneDrive, SharePoint).

## Integration

The following environment variables will be provided in the task execution environment:

- APIDECK_APP_ID
- APIDECK_API_KEY
- APIDECK_CONSUMER_ID
- APIDECK_ISSUE_TRACKING_COLLECTION_ID
- APIDECK_FILE_STORAGE_DRIVE_NAME
- ZEALT_RUN_ID

The following connectors have been configured in the ApiDeck dashboard for testing purposes:

- Issue Tracking: connected to GitHub (Service ID: `github`)
  - Because a `Collection` (which maps to a GitHub repository) cannot be created via ApiDeck APIs, ensure all tasks use the collection ID `APIDECK_ISSUE_TRACKING_COLLECTION_ID`.
  - For each ticket, include `ZEALT_RUN_ID` in the ticket title/subject to isolate task side effects.
  - Note that some fields like `priority` are not supported by GitHub connector.
- File Storage: connected to OneDrive (Service ID: `onedrive`)
  - Because `Create Drives` is not supported for OneDrive via ApiDeck APIs, ensure all tasks use the drive name `APIDECK_FILE_STORAGE_DRIVE_NAME`.
  - For each file, include `ZEALT_RUN_ID` in the filename to isolate task side effects.
  - Only use `List Files` or `Get File` operation to verify task side effects. Avoid using unsupported APIs like `Download`, `Export` or `Share Link`.


## Notes for generating tasks

* Carefully write the final `pytest` test code. When using ApiDeck APIs to verify task side effects, you must use `webFetch` to retrieve the API reference documentation, confirm that the endpoint exists, and ensure the request and response match the documentation.