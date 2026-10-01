# Privacy and retention

## Data inventory

| Data | Purpose | Default retention | Access |
|---|---|---|---|
| Unsaved Ring snapshot/crop | Visitor review and learning proposal | 30 days | Active household members through authorized API |
| User-saved visitor photo | Household-selected reference/history | Persists until a future governed deletion feature exists | Active household members |
| Text visit record | Searchable security history | 1 year | Active household members |
| Approved face identifier and example mapping | Advisory familiar-person suggestions | While the familiar profile is active | Backend and owner-governed profile workflow |
| Profile modification audit event | Accountability for proposals and decisions | No application deletion in the MVP | Active household members; operational access logged |
| Ring OAuth and webhook secrets | Ring account linking and event verification | Until revoked/rotated | Backend secret store only |
| FCM device token | Visitor alert delivery | Until replaced, invalidated, or membership removal | Backend notification service only |

## Enforcement model

Unsaved S3 objects use the fixed `retention=30d` tag and a lifecycle rule. Saving media changes the
controlled tag before expiration. Visit records carry an `expires_at` value; APIs hide them at the
one-year boundary while DynamoDB TTL performs asynchronous physical cleanup. TTL and lifecycle
jobs are cleanup mechanisms, not authorization controls.

The Android client displays cached data offline and must refresh or revoke it after membership
removal. No Ring password, Ring/AWS service credential, raw Rekognition vector, or webhook secret is
stored in the app.

## Household expectations

- Enroll faces only with appropriate consent and notice.
- Household members must be at least 13 and affirm that requirement when accepting an invitation.
- Unknown, low-confidence, conflicting, and face-undetected results remain generic.
- The owner approves canonical profile changes; member proposals and owner decisions are audited.
- Fixed MVP retention is a product constraint, not a claim of compliance with every jurisdiction.

## Launch limitations

The MVP intentionally lacks self-service deletion and export. That is acceptable only for the
limited hackathon demonstration using synthetic or consented data. A real launch requires a
jurisdiction-specific biometric/privacy review and governed access, correction, export, deletion,
account recovery, and incident-response processes.

