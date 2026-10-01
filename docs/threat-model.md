# Knock Knock threat model

## Scope and trust boundaries

The protected assets are Ring OAuth tokens, webhook signing keys, visitor media, face identifiers,
household membership, profile decisions, notification tokens, and the append-only audit trail. The
main boundaries are Ring to API Gateway, Android to the management API, API to SQS, worker to
S3/Rekognition/DynamoDB, and backend to FCM.

The Ring account owner is the sole household administrator. Invited household members are trusted
to review visits but not to change membership or canonical identities. Recognition output is
untrusted advice until a household action confirms or corrects it.

## Threats and controls

| Threat | Primary controls | Residual risk / required evidence |
|---|---|---|
| Forged or replayed Ring event | Raw-body HMAC verification, request-ID conditional claim, five-second acknowledgement | Confirm the production HMAC secret is stored only in Secrets Manager and replay a duplicate against the deployed endpoint. |
| Stolen Ring OAuth token | Server-only encrypted token storage, refresh rotation, no token response to Android | Complete token revocation and rotation drills after Playground credentials exist. |
| Cross-household object access | API Gateway JWT validation plus server-side active membership checks on every object | Run deployed owner/member and unrelated-subject authorization tests. |
| Privilege escalation by a member | Owner-only invitation, removal, and proposal-decision services; client role headers are ignored | Verify deployed Cognito claims cannot override the repository role. |
| False identification | Per-face crops, confidence bands, learning window, conflict suppression, explicit user confirmation | Calibrate with consented diverse fixtures; never describe similarity as identity probability. |
| Group-frame identity mix-up | Detect and track every face independently before `SearchFacesByImage` | Keep the synthetic three-person regression fixture in CI. |
| Media bomb or resource exhaustion | HTTPS host allowlist, byte/duration/frame/face limits, async queue, bounded Lambda concurrency and DLQ | Measure worst-case worker duration after deployment. |
| Notification data leakage | Generic learning/low-confidence copy, safe payload fields, visit ID deep link, no media or token logging | Confirm lock-screen notification settings during the device demo. |
| Presigned URL or log leakage | Short-lived URLs, query strings excluded from logs, structured identifier-only errors | Inspect CloudWatch logs after a live run. |
| Audit tampering | Append-only repository boundary, conditional creation, no application delete route | Apply a dedicated cloud IAM role without update/delete permissions before production. |
| Retention bypass | Fixed S3 tags/lifecycle, API-time expiry filtering, DynamoDB TTL cleanup | S3 and TTL deletion are asynchronous; reconciliation and alarms remain required. |
| Malicious visitor label/content | Treat labels and notes as plain untrusted text; no prompt or command execution | Add server-side length/character constraints before public release. |
| Compromised developer credential | MFA-gated deployment role, short sessions, no IAM user access keys, scoped bootstrap policies | Complete IAM-user MFA enrollment before cloud deployment. |

## Explicit non-goals

The MVP does not infer emotion, intent, criminality, health, race, gender, or age. It does not
automatically unlock, lock out, call authorities, or make safety decisions. It is not a continuous
surveillance platform and does not support public face-dataset ingestion.

## Release gate

Before any public pilot, complete live penetration testing of object-level authorization, privacy
and biometric-law review for the operating jurisdiction, incident response and account recovery,
data-subject request handling, notification privacy review, and an independent false-match study.

