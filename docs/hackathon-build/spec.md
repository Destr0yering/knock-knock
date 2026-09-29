# Technical Spec

## Overview

Knock Knock will evolve the existing Python ports-and-adapters scaffold into a deployed Ring-connected backend and a native Android client. The Android app owns presentation, local caching, notification handling, and authenticated user actions. The backend owns Ring credentials, webhook verification, media fetching, face processing, household authorization, shared records, retention enforcement, and notifications.

The hackathon deployment is serverless on AWS so it has a public HTTPS webhook without an always-running server. The same domain services continue to run locally with simulator, JSON/YAML, logging-alert, and mock-vision adapters. Production adapters replace those boundaries with Ring, SQS, DynamoDB, S3, Rekognition, Cognito, Secrets Manager/KMS, and Firebase Cloud Messaging (FCM).

This specification implements all nine epics in `prd.md`. It intentionally does not implement door-control actions, multi-site business administration, production Ring Appstore certification, or any authoritative identity claim.

## Decisions

### Client

- Native Android in Kotlin using Jetpack Compose and Material 3.
- Minimum SDK 26; target/compile SDK set to the latest stable version available in the installed Android toolchain when the Android project is generated.
- Unidirectional UI state with screen-level ViewModels and Kotlin coroutines/Flow.
- Room provides an encrypted-capable offline cache; the backend remains the shared source of truth.
- Retrofit/OkHttp handles authenticated JSON APIs and presigned media URLs.
- WorkManager performs durable refresh/retry work outside FCM's short callback window.

### Backend

- Python 3.12, FastAPI, Pydantic, and the existing domain/port/service layers.
- Mangum adapts FastAPI to an API Gateway HTTP API Lambda.
- SQS separates the sub-five-second Ring webhook acknowledgement from media and vision processing.
- A Lambda container image runs the worker with OpenCV/FFmpeg-capable clip frame sampling.
- DynamoDB on-demand tables persist shared household state and idempotency records.
- S3 stores encrypted snapshots, clips, and face crops.
- Rekognition provides face detection, enrollment, and matching through the existing `FaceIdEngine` port.
- Cognito User Pools authenticates Android users; application authorization is enforced from household membership records, not trusted client input.
- FCM delivers Android alerts. Notifications contain visit IDs and safe display text, never image bytes or biometric data.

### Deployment

- AWS SAM defines reproducible infrastructure in `infra/template.yaml`.
- One `dev` stack is sufficient for the hackathon; production separation is documented but not provisioned.
- The Ring webhook, OAuth callback, and token exchange endpoints use public HTTPS through API Gateway.
- Local demo mode remains runnable with no cloud or Ring credentials.

### Vision policy

- `AwsRekognitionFaceIdEngine` is the hackathon AI adapter.
- `DeterministicFaceIdEngine` drives repeatable UI and end-to-end tests.
- `OpenCvFaceIdEngine` remains an optional local adapter, not the judging dependency.
- The first 30 days suppress named notification text regardless of match result.
- After day 30, only the configured high-confidence band may produce `Possible match: <name>`.
- No match becomes confirmed without a review action and, when proposed by a member, administrator approval.

## Architecture

```text
Ring API / Playground / upload fixture
                |
                v
      API Gateway HTTP API
                |
        FastAPI Lambda
     /          |          \
Ring webhook  Android API  OAuth callback
     |          |          |
HMAC + ledger  Cognito JWT Secrets Manager/KMS
     |
     v
    SQS --------------> Worker Lambda container
                           |      |       |
                           |      |       +--> Rekognition collection
                           |      +----------> S3 encrypted media
                           +-----------------> DynamoDB records/audit
                                                |
                                                v
                                         FCM alert publisher
                                                |
                                                v
                                     Android notification + sync
                                                |
                                      Room cache + Compose UI
```

### Layering rule

`domain` contains pure models and policy. `services` orchestrate use cases against `ports`. `adapters` translate Ring, AWS, FCM, local storage, and Android network shapes. `api` authenticates, validates, and delegates. No service imports boto3, FastAPI, Android, or a Ring payload type.

### PRD epic mapping

| PRD epic | Technical components |
|---|---|
| Epic 1: onboarding/access | Cognito, `HouseholdMembershipRepository`, invite service, Android auth/household features |
| Epic 2: Ring intake/counting | Ring adapter, webhook ledger, SQS, media sampler, multi-face detector |
| Epic 3: learning period | `LearningPolicy`, household activation timestamp, enrollment service, notification policy |
| Epic 4: person identification | `VisitPerson`, review proposal workflow, profile repository, admin approval endpoints |
| Epic 5: AI suggestions | `FaceIdEngine`, Rekognition adapter, confidence policy, feedback/enrollment service |
| Epic 6: alerts | FCM publisher, device-token repository, Android messaging service and deep links |
| Epic 7: history/search | DynamoDB visit indexes, API filters, Room cache, timeline and visit screens |
| Epic 8: retention | S3 object tags/lifecycle, one-year visit expiry, application-side expiry filtering |
| Epic 9: audit trail | append-only audit repository, conditional writes, dedicated read endpoint/UI |

## File Structure

The existing repository is preserved and extended rather than replaced.

```text
.
├── apps/
│   └── android/
│       ├── app/                         # App entry, navigation, DI, manifest, FCM service
│       ├── core-model/                  # Kotlin API/domain models shared by features
│       ├── core-network/                # Retrofit API, Cognito token interceptor, DTO mapping
│       ├── core-database/               # Room entities, DAOs, migrations, cache repository
│       ├── core-ui/                     # Theme, reusable states/cards, accessibility utilities
│       ├── feature-auth/                # Sign-in, age affirmation, session recovery
│       ├── feature-timeline/            # Visitor timeline, filters, empty/offline states
│       ├── feature-visit/                # Multi-person review and media-save flow
│       ├── feature-profiles/             # Profiles, proposals, admin approvals, audit history
│       ├── feature-household/            # Owner invites/removals and member list
│       ├── feature-settings/             # Ring status, learning status, notification diagnostics
│       ├── build.gradle.kts
│       └── settings.gradle.kts
├── src/knock_knock/
│   ├── domain/
│   │   ├── models.py                    # Household, visit, person, profile, proposal, audit models
│   │   ├── policies.py                  # Learning/confidence/retention/role rules
│   │   └── errors.py                    # Stable domain error types
│   ├── ports/
│   │   ├── camera.py                    # Ring/simulator media boundary
│   │   ├── vision.py                    # Detect, identify, enroll, suppress profile
│   │   ├── repositories.py              # Household/visit/profile/audit/token/ledger ports
│   │   ├── media.py                     # Encrypted media persistence and save-state boundary
│   │   ├── alerts.py                    # Household notification boundary
│   │   └── queue.py                     # Durable event queue boundary
│   ├── services/
│   │   ├── ingest.py                    # Verify/normalize/deduplicate/enqueue Ring events
│   │   ├── processing.py                # Fetch media, sample frames, detect faces, persist visit
│   │   ├── reviews.py                   # Per-person decisions and admin approval workflow
│   │   ├── learning.py                  # Confirmed-frame enrollment and conflict suppression
│   │   ├── households.py                # Owner/member invitations and authorization
│   │   ├── retention.py                 # Expiry metadata and saved-media transitions
│   │   └── notifications.py             # Safe alert text policy
│   ├── adapters/
│   │   ├── camera/
│   │   │   ├── ring.py                  # Official Ring API/webhook/media implementation
│   │   │   ├── simulator.py             # Local deterministic event/image adapter
│   │   │   └── replay.py                # Recorded sanitized event fixture adapter
│   │   ├── vision/
│   │   │   ├── aws_rekognition.py       # Detect/crop/search/index collection adapter
│   │   │   ├── deterministic.py         # Fixture-controlled recognition results
│   │   │   └── opencv.py                # Optional local implementation
│   │   ├── repositories/
│   │   │   ├── dynamodb.py              # Cloud repositories and access patterns
│   │   │   └── local.py                 # Local JSON/YAML/in-memory repositories
│   │   ├── media/
│   │   │   ├── s3.py                    # SSE-KMS media store, tags, presigned reads
│   │   │   └── local.py                 # Private local fixture/media store
│   │   ├── alerts/
│   │   │   ├── fcm.py                   # FCM HTTP v1 sender
│   │   │   └── logging.py               # Local no-network alert sink
│   │   ├── auth/
│   │   │   ├── cognito.py               # JWT claims and subject mapping
│   │   │   └── ring_tokens.py            # Encrypted OAuth token provider/refresh
│   │   └── queue/
│   │       ├── sqs.py                    # Cloud queue adapter
│   │       └── in_process.py             # Local async queue
│   ├── api/
│   │   ├── main.py                      # FastAPI assembly and middleware
│   │   ├── dependencies.py              # Auth/role/container dependencies
│   │   ├── schemas.py                   # Versioned request/response models
│   │   └── routers/
│   │       ├── ring.py                  # Public signed webhook/OAuth endpoints
│   │       ├── demo.py                  # Admin-only fixture ingestion
│   │       ├── households.py            # Invites and membership
│   │       ├── visits.py                # Timeline/detail/review/media-save APIs
│   │       ├── profiles.py              # Profiles/proposals/approval/audit APIs
│   │       └── devices.py               # FCM registration tokens
│   ├── lambdas/
│   │   ├── api_handler.py               # Mangum entry point
│   │   ├── worker_handler.py            # SQS batch/partial-failure entry point
│   │   └── retention_handler.py         # Orphan/expiry reconciliation
│   └── infrastructure/
│       ├── config.py                    # Environment-only configuration
│       └── container.py                 # Local/cloud dependency assembly
├── infra/
│   ├── template.yaml                    # SAM resources, IAM, encryption, lifecycle
│   ├── samconfig.example.toml           # Non-secret deployment defaults
│   ├── Dockerfile.worker                # CV-capable Lambda worker image
│   └── policies/                        # Least-privilege policy fragments/documentation
├── tests/
│   ├── unit/                            # Domain policies/services
│   ├── contract/                        # Ring payload and API schema fixtures
│   ├── integration/                     # DynamoDB/S3/SQS/Rekognition adapter boundaries
│   ├── e2e/                             # Simulator -> visit -> review -> alert workflows
│   └── fixtures/                        # Synthetic/consented non-committed media manifest
├── docs/
│   ├── architecture.md                  # Maintained implementation architecture
│   ├── threat-model.md                  # Assets, trust boundaries, mitigations
│   ├── privacy.md                       # Retention, consent, limitations
│   ├── runbook.md                       # Deploy, rollback, cost, demo recovery
│   └── friction-log.md                  # Devpost bonus evidence
├── .env.example                         # Names only; no credentials
├── .gitignore                           # Secrets, face data, media, tokens, builds
├── pyproject.toml
└── README.md
```

## Data Model

All IDs are UUIDv7/ULID-style sortable opaque strings. Every shared record includes `household_id`; repositories must require it in every read and write path.

### Household

- `household_id`, `ring_account_subject`, `owner_user_id`
- `activated_at`, `learning_ends_at = activated_at + 30 days`
- `status`, `created_at`, `updated_at`
- Fixed policies: `photo_retention_days=30`, `visit_retention_days=365`

### Membership

- `household_id`, `user_id`, `email`, `role = owner|member`
- `age_13_affirmed_at`, `invited_by`, `joined_at`, `removed_at`
- Only one active `owner` in the MVP.

### Visit

- `visit_id`, `household_id`, `ring_event_id`, `ring_request_id`, `device_id`
- `event_type`, `occurred_at`, `status`, `source`
- `person_count`, `processing_error_code`, `created_at`, `expires_at`
- `expires_at` is one year for backend retention; APIs exclude expired visits immediately even if DynamoDB TTL deletion is delayed.

### VisitPerson

- `person_id`, `visit_id`, bounding box, face quality state
- `suggested_profile_id`, `similarity`, `confidence_band`
- `review_state = unresolved|unknown|face_undetected|proposed|confirmed|corrected`
- `confirmed_profile_id`, `reviewed_by`, `reviewed_at`
- `crop_media_id`, `clip_frame_offsets_ms[]`

### Profile

- `profile_id`, `household_id`, `display_name`, `category`, `status`
- `primary_media_id`, `approved_example_count`, `created_by`, timestamps
- `status = active|under_review|suppressed`; suppressed profiles never appear in named alerts.
- Profile records are not hard-deleted through the application.

### ProfileProposal

- `proposal_id`, `household_id`, `visit_id`, `person_id`
- `action = create|correct|merge|rename|suppress`
- old/new values, `proposed_by`, `proposed_at`
- `decision = pending|approved|rejected`, `decided_by`, `decided_at`

### AuditEvent

- Append-only `audit_id`, `household_id`, `actor_user_id`, `actor_role`
- `event_type`, target IDs, before/after hashes or non-sensitive values, reason, timestamp
- Adapter exposes `append` and `list` only. App IAM has no update/delete actions on the audit table.

### MediaObject

- `media_id`, `household_id`, `visit_id`, S3 key, content type, checksum
- `kind = snapshot|clip|face_crop|profile_reference`
- `retention = 30d|saved|profile_reference`, `captured_at`, `expires_at`
- S3 objects are SSE-KMS encrypted and read through short-lived presigned URLs after authorization.

### DeviceToken and EventLedger

- `DeviceToken`: Cognito subject, FCM token hash/encrypted token, platform, updated time.
- `EventLedger`: Ring `request_id` as a conditional-write idempotency key with short TTL.

## DynamoDB Access Plan

Use separate on-demand tables for clarity and least-privilege policies: `Households`, `Memberships`, `Visits`, `Profiles`, `AuditEvents`, `DeviceTokens`, and `EventLedger`. The hackathon scale does not justify a dense single-table design.

Required indexes:

- Visits: `household_id + occurred_at` timeline index; `household_id + profile_id` materialized lookup key for filters.
- Profiles: `household_id + normalized_display_name` uniqueness/search index.
- Proposals: stored with Profiles table using a distinct key prefix and indexed by household/decision time.
- Audit: `household_id + target_id + timestamp` index.
- Memberships: `user_id` index to resolve household after Cognito authentication.

## Media And Multi-Face Processing

1. Fetch the Ring event snapshot and, when available for the event, its media clip.
2. Verify content type, byte limit, checksum, and media URL scheme before storage.
3. Store original media under a private S3 prefix with `retention=30d` and SSE-KMS.
4. Sample clip frames at bounded intervals; cap decoded duration, resolution, frame count, and CPU time.
5. Run `DetectFaces` on each candidate frame and retain bounding boxes/quality metadata.
6. Crop each detected face separately. This is required because Rekognition `SearchFacesByImage` searches the largest face in its input image.
7. Deduplicate near-identical crops across adjacent frames, keeping several quality/pose-diverse examples per detected person.
8. Call `SearchFacesByImage` per crop, aggregate results for the same detected person, and apply the domain confidence policy.
9. Store only the bounded set of selected crops and recognition diagnostics required for review.
10. On an approved profile confirmation, call `IndexFaces` for accepted examples with the profile ID as external identity metadata.

Watermark-aware tests must include the mandatory Ring watermark visible in snapshots and clips. The system must never crop or alter media for the purpose of removing the watermark.

## Data Flow

### A. Ring event to shared alert

1. Ring sends an HTTPS webhook to `POST /v1/webhooks/ring`.
2. API verifies HMAC-SHA256 over raw bytes before parsing.
3. The Ring adapter normalizes the JSON:API payload.
4. `EventLedger.claim(request_id)` conditionally writes the idempotency record.
5. The API enqueues a compact normalized event and returns HTTP 200 within five seconds.
6. Worker fetches snapshot/clip using encrypted per-account OAuth tokens.
7. Worker samples media, detects/crops people, requests Rekognition suggestions, stores media and visit records.
8. Notification policy reads the 30-day learning state and confidence bands.
9. FCM sends safe text plus `visit_id`; Android deep-links to the visit.
10. Android fetches the authorized visit, caches it in Room, and renders person cards.

### B. User review to learning feedback

1. User selects existing, unknown, face undetected, or proposes a new/corrected identity.
2. Android sends a conditional review request containing the current visit version.
3. Service authorizes membership and detects concurrent edits.
4. Owner decisions apply immediately; member profile changes create a pending proposal.
5. Service appends an audit event before publishing the new shared state.
6. Approved confirmed crops are enrolled through `FaceIdEngine.enroll`.
7. Profile state and example count update; all clients see the new visit version on sync.

### C. Retention

1. Unsaved S3 objects carry `retention=30d`; an S3 Lifecycle rule expires that tagged class.
2. Saving media retags it `retention=saved` through an authorized backend action before expiry.
3. Visit rows carry a one-year `expires_at`; API filters expired rows immediately and DynamoDB TTL removes them asynchronously.
4. Scheduled reconciliation records retention outcomes and detects orphaned media. It cannot change the fixed policy from a client request.
5. Audit events are not exposed to application deletion APIs.

## API Contracts

All management endpoints require a Cognito JWT. Every mutation accepts `Idempotency-Key`; versioned resources use `If-Match` or a body `version` to prevent silent overwrite.

### Ring and demo ingestion

- `POST /v1/webhooks/ring` — public but HMAC-authenticated; returns `{status, request_id}`.
- `GET /v1/ring/oauth/start` — owner only; creates state/PKCE metadata and redirects to Ring.
- `GET /v1/ring/oauth/callback` — exchanges the authorization code server-side and stores encrypted tokens.
- `POST /v1/demo/events` — owner only and disabled outside `dev`; accepts a named sanitized fixture, never an arbitrary server path.

### Household and devices

- `GET /v1/me/household`
- `POST /v1/households/{id}/invitations` with `{email}` — owner only.
- `POST /v1/invitations/{token}/accept` with `{age_13_affirmed: true}`.
- `DELETE /v1/households/{id}/members/{user_id}` — owner only; removes access, not audit history.
- `PUT /v1/devices/fcm-token` with `{token, platform:"android"}`.

### Visits

- `GET /v1/visits?cursor=&profile_id=&state=&category=&saved=&from=&to=`
- `GET /v1/visits/{visit_id}` — includes person cards, media availability, and current versions.
- `POST /v1/visits/{visit_id}/people/{person_id}/reviews`

Review request:

```json
{
  "decision": "existing_profile|unknown|face_undetected|new_profile|correction",
  "profile_id": "optional",
  "proposed_name": "optional",
  "category": "optional",
  "note": "optional",
  "visit_version": 3
}
```

- `PUT /v1/visits/{visit_id}/media/{media_id}/saved` with `{saved:true}` — changes the retention tag; no delete endpoint.

### Profiles and audit

- `GET /v1/profiles?query=&status=`
- `GET /v1/profiles/{profile_id}` — profile, examples summary, related modifications.
- `GET /v1/profile-proposals?decision=pending` — owner sees approval queue.
- `POST /v1/profile-proposals/{proposal_id}/decision` with `{decision:"approved|rejected", reason}` — owner only.
- `GET /v1/audit?profile_id=&visit_id=&cursor=` — shared read-only audit history.
- There is no profile hard-delete or audit-delete endpoint in the MVP.

### Response envelope and errors

Successful list responses use `{items, next_cursor}`. Errors use:

```json
{
  "error": {
    "code": "stable_machine_code",
    "message": "safe user-facing explanation",
    "request_id": "trace identifier",
    "retryable": false
  }
}
```

No response or log exposes Ring tokens, FCM credentials, HMAC keys, raw webhook bodies, presigned URL query strings, or Rekognition face vectors.

## Components And Responsibilities

### Android application

Implements: `prd.md > Epic 1`, `Epic 4`, `Epic 6`, `Epic 7`, `Epic 9`.

Renders onboarding, timeline, multi-person review, profile/proposal screens, owner controls, audit history, and retention states. It stores only API data required for offline display and never stores Ring/AWS service credentials.

### Ring camera adapter

Implements: `prd.md > Epic 2`.

Verifies signed events, parses relevant motion/button events, refreshes OAuth tokens, downloads snapshots/clips, respects rate limits/privacy zones, and reports typed boundary errors. It targets `https://api.amazonvision.com` and keeps staging/production configuration separate.

### Event ingestion and SQS

Implements: `prd.md > Epic 2` and error criteria.

Claims Ring request IDs once, acknowledges quickly, queues durable work, retries transient errors with backoff, and sends exhausted items to a dead-letter queue. SQS visibility timeout is at least six times the worker timeout.

### Media processor and vision engine

Implements: `prd.md > Epic 2`, `Epic 3`, `Epic 5`.

Samples bounded frames, finds every visible face, creates separate person candidates, aggregates suggestions, applies confidence/learning policy, and enrolls only administrator-approved examples.

### Household authorization service

Implements: `prd.md > Epic 1`, `Epic 4`.

Maps Cognito subjects to household membership, enforces owner-only actions, records 13+ affirmation, and treats roles sent by clients as untrusted. Cognito authenticates; DynamoDB membership records authorize.

### Review and learning services

Implements: `prd.md > Epic 3`, `Epic 4`, `Epic 5`, `Epic 9`.

Persist per-person decisions, create member proposals, apply owner decisions, append audit events, detect conflicts, suppress disputed profiles, and send approved examples to the selected face engine.

### Notification service

Implements: `prd.md > Epic 6`.

Builds generic learning-period/low-confidence alerts or qualified high-confidence alerts, includes detected-person count, sends FCM data for deep links, and leaves the visit record as the source of truth if delivery fails.

### Visit/search repository

Implements: `prd.md > Epic 7`.

Provides cursor pagination and the required filters without cross-household access. Android Room mirrors the current slice and marks stale/offline content clearly.

### Retention service

Implements: `prd.md > Epic 8`.

Applies fixed expiry metadata, saves selected media by changing controlled S3 retention tags, hides expired visits at query time, and reconciles asynchronous storage cleanup.

### Audit repository

Implements: `prd.md > Epic 9`.

Offers append and read only, uses conditional creation, and runs under an IAM role with no update/delete permissions. Operational break-glass access is outside the app and logged through AWS controls.

## External APIs And Dependencies

### Ring

- [Ring API development guide](https://developer.amazon.com/docs/ring/develop.html)
- [Ring Partner API documentation](https://developer.amazon.com/docs/ring/api-documentation.html)
- [Ring API release notes](https://developer.amazon.com/docs/ring/release-notes.html)
- [Ring hello-world sample](https://github.com/AmazonAppDev/ring-api-helloworld)

Current constraints incorporated here: HTTPS webhooks return 200 within five seconds, idempotency uses `request_id`, staging supports up to ten users, the Developers Playground can simulate/test APIs, and Ring media carries a mandatory visible watermark.

### AWS

- [Rekognition collection search](https://docs.aws.amazon.com/rekognition/latest/dg/collections-search-faces.html)
- [Cognito user-pool groups](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html)
- [Lambda with SQS](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html)
- [S3 Lifecycle management](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [DynamoDB TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)

DynamoDB TTL is cleanup, not exact-time access control: the API filters one-year-expired rows because AWS may physically remove TTL items days later.

### Android and notifications

- [Jetpack Compose](https://developer.android.com/develop/ui/compose/documentation)
- [Room](https://developer.android.com/training/data-storage/room)
- [Persistent work with WorkManager](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [Firebase Cloud Messaging for Android](https://firebase.google.com/docs/cloud-messaging/android/receive-messages)

Longer notification work is delegated to WorkManager rather than performed inside the short FCM callback window.

### Python dependencies to add

- `mangum` for API Gateway/Lambda adaptation.
- `boto3` for Rekognition, DynamoDB, S3, SQS, KMS/Secrets Manager, and Cognito admin operations.
- `PyJWT[crypto]` or a maintained Cognito JWT verifier for local/test verification; API Gateway JWT authorizer remains the first cloud gate.
- `firebase-admin` or an OAuth2 HTTP v1 sender for FCM.
- `opencv-python-headless` and bounded video decoding in the worker image.
- `aws-lambda-powertools` for structured logging, metrics, tracing, and idempotency helpers where it reduces custom code.

Versions will be pinned by lockfiles generated during implementation after compatibility checks in the actual environment.

## AI Usage

### Recognition flow

- Rekognition `DetectFaces` supplies face boxes and quality signals.
- Per-face crops are searched against a collection; raw similarity is retained for diagnostics but mapped to product bands.
- A calibration fixture set determines the initial `high`, `review`, and `unknown` thresholds. No threshold is described as a probability of identity.
- Multiple confirmed examples are indexed for a profile; poor-quality, duplicate, or unapproved frames are rejected.
- Corrections create learning jobs. Conflicted profiles become `under_review` and do not generate named notifications.

### Safety and privacy rules

- Never infer age, race, gender, emotion, health, criminality, or intent.
- Never use a recognition result to unlock, deny entry, call authorities, or trigger another consequential action.
- Never label a visitor as confirmed without a household action.
- Store Rekognition identifiers and profile mappings server-side only.
- Use synthetic, consented, or properly licensed media for repository fixtures and the demo.
- Measure false matches and non-matches across lighting, angle, occlusion, group visits, masks/glasses, skin tones, and the Ring watermark.

## Security And Privacy

- API Gateway validates Cognito JWTs for management routes; Ring webhook uses HMAC over raw bytes.
- Every service method also enforces household membership and role, preventing broken object-level authorization.
- Ring tokens, FCM credentials, and client secrets live in Secrets Manager encrypted with KMS and are never returned to Android.
- S3 blocks public access, uses SSE-KMS, and serves short-lived presigned GET URLs only after authorization.
- DynamoDB, SQS, and logs use encryption; CloudWatch logs exclude raw media and secrets.
- IAM roles are split between API, worker, retention, and deployment. The app runtime cannot delete audit rows.
- Upload fixtures accept only bounded JPEG/PNG content after signature/magic-byte validation; clips are bounded by duration, size, and decode limits.
- Presigned URLs and external media URLs are never followed to arbitrary hosts by the backend; Ring downloads use expected HTTPS flows and size limits.
- `.gitignore` continues to exclude `.env`, tokens, face data, media, local databases, APKs, and credentials.
- A repository threat model covers token theft, webhook forgery, cross-household access, replay, media bombs, prompt/content injection in labels, misidentification, and notification leakage.

## Local And Cloud Environments

### Local demo

- Simulator/replay camera adapter.
- Deterministic vision adapter with fixture-declared face boxes and suggestions.
- Local media directory excluded from Git.
- JSON/YAML or SQLite repositories and logging alerts.
- Android emulator points to the local API and can inject a synthetic notification/deep link.

### AWS development stack

- Real Ring Developer Playground/staging webhook.
- Rekognition collection, encrypted S3, DynamoDB, SQS/DLQ, Cognito, Lambda/API Gateway, and FCM.
- No production Ring certification is required for the Devpost demo.
- Real-device staging, if used, follows Ring's Test phase; the official guide currently notes US-located devices and an active Ring Protection subscription for full real-device testing.

## Testing Strategy

### Unit tests

- Learning-period and confidence notification policy.
- Role/approval matrix and 13+ affirmation requirement.
- Multi-person grouping and no-face outcomes.
- Retention timestamps and saved-media state.
- Conflict suppression and immutable audit event construction.

### Contract tests

- Recorded sanitized Ring motion/button payloads and HMAC signatures.
- Duplicate `request_id` acknowledgement.
- Ring media redirect/download behavior and typed failures.
- API request/response snapshots for Android DTO compatibility.
- Rekognition responses for multiple crops, empty matches, and threshold edges.

### Integration tests

- DynamoDB conditional writes and household isolation.
- S3 encryption/tags/presigned URL authorization and lifecycle configuration inspection.
- SQS partial batch failure, retry, and DLQ behavior.
- Cognito JWT/subject-to-membership authorization.
- FCM sender payloads without live delivery in default CI.

### Android tests

- Compose UI tests for empty timeline, learning banner, group review, face-undetected, expired photo, approval queue, and audit history.
- Room migration and offline cache tests.
- Deep-link tests from FCM `visit_id` to the correct visit.
- Accessibility checks for labels, contrast, touch targets, and scalable text.

### End-to-end acceptance tests

- Simulator event -> queued processing -> three person cards -> generic count alert.
- Member proposes correction -> owner approves -> audit entry -> shared state -> enrollment.
- Day-31 high-confidence result -> qualified named alert; low-confidence result -> generic alert.
- Photo expiration/saved-media scenarios and one-year log filtering with an injected clock.
- Worker failure -> visible retry/error state without losing the Ring event.

## Risks And Verification

### Risk 1: Ring access/setup delay

Mitigation: implement and film the official Developers Playground/simulator path first; keep sanitized replay fixtures. Verify webhook HMAC, five-second response, duplicate delivery, and media fetch separately. Do not wait for physical-device certification.

### Risk 2: Multi-person matching is incorrectly implemented

Mitigation: detect/crop each face before collection search; test a three-person fixture and assert three stable person records. Do not call `SearchFacesByImage` once on the group frame and assume all faces were searched.

### Risk 3: Lambda computer-vision packaging or timeout

Mitigation: use a worker container image, cap clip duration/frames/resolution, process async through SQS, and keep snapshot-only fallback. Verify cold start and worst-case execution before demo week.

### Risk 4: Recognition demo variability

Mitigation: use consented fixed media, record expected confidence bands, keep a deterministic adapter for UI rehearsal, and label the live Rekognition result honestly. Never tune the demo by hiding failures.

### Risk 5: Shared-account authorization expands scope

Mitigation: one household, two roles, invitation-only accounts, server-enforced membership, no self-service organizations. Build owner and one member demo accounts only.

### Risk 6: Retention is assumed to be exact

Mitigation: filter expired records in application queries, use S3 Lifecycle/DynamoDB TTL for physical cleanup, and test with an injected clock. Display “photo expired” from metadata even if asynchronous deletion is pending.

### Risk 7: Cost overrun

Mitigation: use on-demand/serverless resources, low concurrency, bounded media, log retention, budgets already configured, and teardown commands in the runbook. No provisioned capacity, NAT Gateway, always-on database, or ECS service.

## Verification Checkpoints

1. Local Python unit/contract suite passes with no credentials.
2. Android app builds, launches, and renders fixture timeline on an emulator.
3. Local end-to-end simulator creates a multi-person visit and review flow.
4. AWS SAM stack deploys with least-privilege roles and no public S3 access.
5. Cognito owner/member authorization rejects cross-role actions.
6. Ring Playground/staging event reaches the HTTPS webhook and is acknowledged within five seconds.
7. Worker returns separate candidates for every face in the group fixture.
8. Rekognition enroll/search path returns a tentative suggestion and correction updates learning/audit state.
9. FCM deep link opens the correct visit on a physical Android device or Google APIs emulator.
10. Retention, error recovery, README setup, threat model, friction log, and three-minute demo script are reviewed before recording.

## Demo And Submission Flow

### Live demo path

1. Show the Android timeline in its clear learning-period state.
2. Trigger an official Ring Playground/simulator motion or button event.
3. Show the count-aware generic notification and open the linked visit.
4. Review three person cards: existing profile, proposed new identity, and unknown/face-undetected.
5. Switch to owner approval, approve the proposal, and show the immutable modification entry.
6. Show a prepared post-learning event: one high-confidence “Possible match” and one low-confidence generic result.
7. Filter the history and show an expired-photo placeholder alongside the retained one-year event record.
8. Briefly show the working Ring webhook, Rekognition calls, AWS architecture, and privacy limits.

### Demo fallback order

1. Ring Playground/simulator + deployed AWS stack.
2. Sanitized recorded Ring webhook replay + deployed AWS stack.
3. Fully local deterministic pipeline + Android app, with logs/screenshots from the verified deployed integration.

### Submission evidence

- Public or reviewer-accessible GitHub repository with setup/run/test instructions and license decision.
- Under-three-minute public English YouTube/Vimeo demo.
- Architecture diagram, test output, Ring integration evidence, AWS services list, and product feedback.
- `docs/friction-log.md` capturing concrete Ring/AWS onboarding issues for the optional judging bonus.
- Explicit disclosure that recognition is advisory and access control is not implemented.

## Definition Of Technically Ready

The MVP is technically ready when a judge can follow the README, observe a working Ring simulator/API call in code and in the demo, see one event traverse the deployed queue/vision/storage/notification path, review multiple people independently on Android, approve a profile change with an immutable audit entry, and verify that low-confidence or learning-period output never overstates identity.
