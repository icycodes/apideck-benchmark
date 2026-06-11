ApiDeck webhooks send real-time event notifications (like HRIS employee profile updates) to a single endpoint. Securing these webhooks ensures that payloads genuinely originate from ApiDeck and prevent unauthorized data injection.

You need to implement an Express.js webhook route that intercepts incoming POST requests, extracts the `x-apideck-signature` header, and cryptographically verifies the request body against your configured webhook secret.

**Constraints:**
- Must strictly follow the ApiDeck signature verification algorithm (HMAC SHA-256).
- Return a `401 Unauthorized` HTTP status code if the signature is missing or invalid.
- Only process the HRIS payload if the signature is successfully validated.