# Privacy and retention

Internal engineering policy for the Ring snapshot pilot. This is not a public notice or legal
review. The self-service deletion path is implemented in source but is not live until the stack
and configured Android build are deployed and the end-to-end flow is checked.

## Data inventory

| Data | Purpose | Retention / deletion | Access |
|---|---|---|---|
| Ring snapshot and face crops | One still JPEG for visitor review and advisory face analysis; video is not fetched | Unsaved S3 objects expire after 30 days; account deletion removes all active objects under the household prefix | Authenticated owner through a short-lived signed URL |
| Visit and review rows | Visitor history and owner corrections, including owner-entered labels for one visit | DynamoDB TTL targets 365 days; deletion worker removes active rows; visit labels do not create face templates | Owner-scoped API |
| Rekognition face references | Advisory matches for a household | Ring processing uses one deterministic Rekognition collection per owner; deletion calls `DeleteCollection` | Worker role only |
| Ring account tokens and consent | OAuth refresh/access and evidence of owner consent | Removed during account deletion; owner must also remove the app in Ring Appstore to revoke the Ring-side one-way link | Backend only |
| Push token | Generic alert delivery after separate opt-in | Removed during account deletion or token revocation | Backend notification service only |
| Deletion receipt record | Lets a signed-out owner poll job completion | Receipt hash only; expires after 30 days | Public status endpoint requires the unguessable receipt |
| Ring event dedupe record | Prevent Ring webhook retries from duplicating work | Seven-day TTL; contains Ring request ID and is not mapped to an owner | Backend only |
| Service and deletion operations logs | Security, diagnostics, and failed-job recovery | Lambda/API logs are configured for 14 days; SQS messages expire after four days and deletion DLQ messages after 14 days | Restricted AWS operators |
| Local journal | Private visit records, face examples, encrypted local database and app preferences | Account deletion closes and deletes app databases, private vault and local preferences; normal Android uninstall also removes app-private data | Device owner after device unlock |

## Deletion behavior

The owner must be signed in and type `DELETE`. The API immediately writes a household deletion
tombstone, which blocks new Ring event processing, then submits an encrypted SQS deletion job. The
worker removes the household's S3 objects, visit rows, device tokens, Ring tokens, and its isolated
Rekognition collection. It removes the household record and deletes the Cognito user last. A
one-time receipt allows status checks after local tokens are erased. Failed jobs are retried and
retained in a deletion dead-letter queue for operator recovery; the service must not report
completion while cleanup has failed. The app also erases local databases, encrypted media, and
sign-in state after the server accepts the request.

Ring uses a one-way Appstore account-link flow. Knock Knock cannot revoke that Ring-side link by
itself; the owner must open Ring Appstore > My Apps > Knock Knock > Remove App. Ring invalidates its
tokens and stops webhooks when the user removes the app. This Ring-side action is separate from
deleting the Knock Knock account.

“Complete” means primary application data and account credentials have been removed. It does not
mean every backup or operational record vanishes immediately. The Household and Visit tables have
DynamoDB point-in-time recovery enabled; deleted values can remain recoverable in backups for up to
35 days. Event dedupe rows expire after seven days, service logs after 14 days, and deletion-job
receipts after 30 days. Failed deletion queue messages can remain in the encrypted dead-letter queue
for up to 14 days. A minimal household-subject tombstone has a DynamoDB TTL expiration set five
minutes after the current sign-in token expires to prevent that token from restarting processing;
TTL cleanup can occur later. No visitor names, images or face vectors are written to application
logs.

## Enforcement and safeguards

- Every Ring media object is stored under `households/{owner-sub}/`; deletion enumerates only that
  exact prefix and deletes all object versions and delete markers in S3-sized batches.
- Ring worker searches only the owner's Rekognition collection. It does not search the legacy
  shared collection. The API's generic, unscoped profile and visitor routes are disabled for the
  Ring service deployment.
- Ring processing consent is versioned and checked before snapshot retrieval. A deletion tombstone
  is checked again before visit persistence. The flow requests still JPEG images only.
- FCM messages contain a generic alert and visit ID only. Push registration requires separate
  owner opt-in; account deletion removes all tokens for that owner.
- Android private records use SQLCipher and an Android Keystore-wrapped key. Deletion removes the
  wrapping key and local databases. It does not promise physical sanitization of flash storage.
- Face results are advisory. Do not use the system for access control, emergency response, or
  consequential identity decisions. Test with consenting adults and avoid minors, neighbors and
  passersby.

## Publication gates

- The public notice source is configured for Got2Get2Work and
  got2get2worksupport@gmail.com. Confirm that this mailbox is monitored and publish the notice at
  a stable public URL after deployment and privacy review.
- Deploy the IaC and configured app build; verify request acceptance, processing stop, every deletion
  target and the signed-out receipt flow before personal Ring data is used.
- Keep the legacy Rekognition collection isolated from new Ring processing. The read-only inventory
  on 2026-10-22 found `knock-knock-dev-faces` with zero indexed faces. It remains in place; no
  collection was deleted. New Ring processing uses a distinct collection per household.
- Obtain qualified privacy review for the pilot locations and update platform disclosures to match
  the deployed data flows.
