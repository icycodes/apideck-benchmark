# ApiDeck Benchmark Research Plan

## 1. Library Overview
*   **Description**: ApiDeck is a Unified API platform that allows developers to integrate with 200+ SaaS services across categories like CRM, HRIS, Accounting, and File Storage through a single, standardized interface. It provides "Unify" (the unified APIs), "Vault" (a managed UI for user authentication/connections), and "Ecosystem" (white-labeled integration marketplaces).
*   **Ecosystem Role**: Acts as an abstraction layer between a software application and multiple third-party integrations, eliminating the need to build and maintain individual connectors for every service (e.g., Salesforce, Xero, Workday).
*   **Project Setup**:
    1.  **Account**: Create an account at `apideck.com` and obtain an `API Key` and `App ID`.
    2.  **CLI**: `brew install apideck-libraries/tap/apideck`
    3.  **SDK Installation**:
        *   Node.js: `npm install @apideck/sdk`
        *   Python: `pip install apideck-unify`
    4.  **Initialization**:
        ```typescript
        import { Apideck } from "@apideck/sdk";
        const apideck = new Apideck({
          apiKey: "REPLACE_WITH_API_KEY",
          appId: "REPLACE_WITH_APP_ID",
          consumerId: "REPLACE_WITH_USER_ID" // Unique ID for your end-user
        });
        ```

## 2. Core Primitives & APIs
*   **Unified APIs**: Standardized models for different business domains.
    *   **CRM**: `crm.contacts.list()`, `crm.opportunities.create()` [Docs](https://developers.apideck.com/apis/crm/reference.md)
    *   **Accounting**: `accounting.invoices.list()`, `accounting.payments.add()` [Docs](https://developers.apideck.com/apis/accounting/reference.md)
    *   **HRIS**: `hris.employees.list()`, `hris.timeOffRequests.add()` [Docs](https://developers.apideck.com/apis/hris/reference.md)
*   **Vault**: Manages the lifecycle of connections and provides the authentication UI.
    *   `vault.sessions.create()`: Generates a secure session for embedding the connection UI. [Docs](https://developers.apideck.com/apis/vault/reference.md)
*   **Proxy (Unified Pass-through)**: Allows making direct calls to the downstream API for fields/operations not covered by the unified model.
    ```typescript
    const result = await apideck.vault.proxy({
      method: 'POST',
      path: '/services/data/v53.0/sobjects/Contact',
      raw: true // Accesses the raw downstream response
    });
    ```
    [Docs](https://developers.apideck.com/guides/pass-through.md)
*   **Webhooks**: Receive real-time updates from integrations via a single endpoint. [Docs](https://developers.apideck.com/guides/webhooks.md)

## 3. Real-World Use Cases & Templates
*   **File Picker**: A pre-built UI component to browse and upload files across Google Drive, Dropbox, etc. [Guide](https://developers.apideck.com/guides/file-picker.md)
*   **ATS to HRIS Sync**: Automatically pushing hired candidates from an ATS (like Greenhouse) into an HRIS (like Hibob). [Guide](https://developers.apideck.com/guides/sync-applicant.md)
*   **Expense Management**: Automated syncing of corporate card transactions into accounting systems like Xero or QuickBooks. [Guide](https://developers.apideck.com/guides/expenses-bills.md)
*   **Sample Apps**: Official samples for Next.js and Remix showing Vault session creation and Unified API calls. [Samples Repo](https://github.com/apideck-samples)

## 4. Developer Friction Points
*   **Refresh Token Race Condition**: Occurs when multiple concurrent requests attempt to refresh an expired OAuth token simultaneously, leading to `invalid_grant` errors. Developers must use `validateConnectionState` to serialize refreshes. [Issue/Guide](https://developers.apideck.com/guides/refresh-token-race-condition.md)
*   **Field Mapping Complexity**: Mapping custom fields from downstream services (like HubSpot custom properties) into the Unified Model requires specific configuration in the ApiDeck dashboard or via API. [Guide](https://developers.apideck.com/guides/field-mapping.md)
*   **Webhook Signature Verification**: Implementing robust security for webhooks is often overlooked but critical for production. [Guide](https://developers.apideck.com/guides/webhook-signature-verification.md)

## 5. Evaluation Ideas
*   **Simple**: Initialize the SDK and list all CRM contacts with pagination.
*   **Simple**: Create a new folder in a user's connected File Storage provider (e.g., Google Drive).
*   **Medium**: Implement a webhook receiver that verifies the `x-apideck-signature` and logs HRIS employee updates.
*   **Medium**: Use the Proxy API to fetch a custom field from a Salesforce Contact that is not part of the Unified CRM model.
*   **Complex**: Implement a robust "Sync" function that handles the Refresh Token Race Condition using `validateConnectionState` before making parallel API calls.
*   **Complex**: Build a multi-step workflow that creates an invoice in an Accounting system and then marks it as paid using the `accounting.payments.add` resource.
*   **Complex**: Configure and test a custom field mapping for a specific connector to ensure proprietary data is returned in the Unified API response.

## 6. Sources
1. [ApiDeck Developer Documentation](https://developers.apideck.com): Core documentation and API references.
2. [ApiDeck llms.txt](https://developers.apideck.com/llms.txt): High-level overview for LLM consumption.
3. [ApiDeck llms-full.txt](https://developers.apideck.com/llms-full.txt): Full index of all documentation pages.
4. [ApiDeck Samples GitHub](https://github.com/apideck-samples): Collection of reference implementations.
5. [Refresh Token Race Condition Guide](https://developers.apideck.com/guides/refresh-token-race-condition.md): Detailed explanation of a common concurrency issue.
6. [Field Mapping Guide](https://developers.apideck.com/guides/field-mapping.md): Documentation on extending unified models.