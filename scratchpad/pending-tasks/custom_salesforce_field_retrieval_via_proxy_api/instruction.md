The Unified CRM model normalizes standard fields, but sometimes proprietary or custom fields (e.g., specific Salesforce objects) are required. The ApiDeck Proxy API allows you to bypass the unified model and make direct requests to the downstream provider.

You need to write a function using the SDK's Proxy API to execute a direct `GET` request to the Salesforce endpoint `/services/data/v53.0/sobjects/Contact/{id}` to fetch a specific contact's raw data.

**Constraints:**
- You MUST use `apideck.vault.proxy()`.
- The `raw` property must be set to `true` to access the exact downstream response.
- Do NOT use the standard `crm.contacts.retrieve()` method.