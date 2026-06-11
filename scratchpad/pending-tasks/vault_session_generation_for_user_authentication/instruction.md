ApiDeck Vault acts as a managed connection UI and token lifecycle manager. To allow end-users to authorize third-party integrations, you must securely instantiate a session token.

You need to create a server-side function that utilizes the Vault API to generate a secure session for a specific end-user, returning the session token needed to embed the ApiDeck Vault UI in a frontend application.

**Constraints:**
- Must use the `vault.sessions.create()` method.
- Do NOT expose your primary API keys in the response; only return the `session_token` and `session_uri`.