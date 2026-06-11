ApiDeck's Accounting API standardizes interactions with systems like Xero or QuickBooks. A common multi-step workflow involves generating an invoice and then immediately logging a payment against it.

You need to build a script that first creates a new invoice using the Accounting API, parses the response to retrieve the generated invoice ID, and then records a payment to mark that specific invoice as fully paid.

**Constraints:**
- Must use `accounting.invoices.add()` and `accounting.payments.add()`.
- Ensure the payment payload references the newly created invoice ID.
- Check the HTTP response status of the invoice creation step; if it fails, do NOT attempt the payment step.