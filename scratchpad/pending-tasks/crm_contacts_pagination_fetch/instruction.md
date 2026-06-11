ApiDeck's Unified CRM API allows developers to retrieve contacts across multiple different CRM platforms (like Salesforce or HubSpot) using a single standardized data model. 

You need to initialize the `@apideck/sdk` and write a Node.js function that fetches all CRM contacts for a given user, automatically handling cursor-based pagination until all records are retrieved from the downstream integration. 

**Constraints:**
- Must instantiate the client using your `apiKey`, `appId`, and a specific `consumerId`.
- Must use the `crm.contacts.list()` method.
- Return a single flattened array containing all retrieved contact objects.