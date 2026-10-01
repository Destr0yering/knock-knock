# Build Notes

## Onboarding

- Participant: Thomas Ohmstead.
- Project name chosen: **Knock Knock**.
- Tagline chosen: **"Know who's at the door before the knock knock!"**
- Primary hackathon scenario: daily private-family use, while preserving a future path for businesses.
- Core interaction: Ring freeze frame -> suggested known identity when credible -> user confirmation/correction -> unknown visitor categorization and tagging -> durable visit history.
- Product boundary: the user, not the model, is the identity authority.
- Implementation model: Codex builds the Android application; Thomas directs product decisions and evaluates the result.
- Onboarding deepening rounds: not applicable.
- Active shaping moments: Thomas narrowed the demo from a universal family/business platform to private-family use and specified freeze-frame-based user tagging.

## Scope

- Selected a dual-input strategy: the official Ring API/simulator is the judging and production path; uploaded freeze frames provide deterministic development and demo fallback through the same adapter.
- Confirmed the MVP centers on AI-aided identification, alerts, categorization, and visitor logging.
- Confirmed that identity matching is advisory and user-verified.
- Deferred automatic unlocking and all other access-control actions until after the MVP.
- Deferred multi-site and business administration, continuous surveillance, demographic/emotion inference, and commercial Appstore launch.
- Scheduled a code-complete target for October 16, testing through October 20, demo/documentation on October 21, and submission on October 22 ahead of the October 23 deadline.
- Inspiration reviewed: familiar-face alerts, Ring-style event timelines, and local-first security retention controls. The chosen direction combines their useful patterns while emphasizing visible uncertainty and user authority.
- Scope deepening rounds: 0; Thomas directed Codex to write the scope once the mandatory decisions were resolved.
- Active shaping moment: Thomas kept the long-term vision broad—identification, alerts, logging, and future automatic door functions—while agreeing to exclude autonomous door actions from the hackathon MVP.

## Product Requirements

- Established a 30-day learning period in which alerts remain generic while users identify visitors and the app gathers multiple confirmed facial examples from Ring clips.
- After the learning period, high-confidence results may produce tentative named alerts; low-confidence, conflicting, unknown, and face-undetected results remain generic.
- A visit reports the number of people detected and provides a separate identity decision for every detected person.
- Confirmed that the product should continuously learn from confirmations, corrections, merges, and relabeling.
- Established one shared household data space. The Ring account owner is the sole administrator; invited household members must be at least 13.
- Only the administrator can invite/remove members or approve canonical profile changes. Member proposals and administrator decisions update the shared visit state.
- Every profile modification retains an attributable, immutable audit entry.
- Fixed retention: unsaved photos expire after 30 days, explicitly saved photos persist, and text visitor logs remain for one year. Household users cannot weaken these schedules or manually delete security logs in the MVP.
- PRD deepening rounds: 1 focused edge/permissions round covering multiple faces, face-undetected events, shared access, correction behavior, auditability, and retention.
- Active shaping moments: Thomas replaced a generic privacy-delete control with fixed security retention and an immutable audit trail; he also required shared household access while reserving administration for the Ring account owner.

## Technical Specification

- Thomas delegated stack selection to Codex and approved the recommended native Android, Python/FastAPI, AWS serverless, Ring official API, Cognito, Rekognition, and FCM direction.
- Preserved the existing ports-and-adapters Python scaffold and specified production adapters rather than restarting the backend.
- Selected Kotlin/Jetpack Compose, Room, Retrofit/OkHttp, WorkManager, and FCM for Android.
- Selected API Gateway + Lambda/Mangum, SQS/DLQ, a CV-capable worker Lambda container, DynamoDB, S3/KMS, Rekognition, Cognito, Secrets Manager, and SAM for AWS.
- Kept local simulator/replay, deterministic vision, local storage, and logging alerts for credential-free development and demo recovery.
- Critical technical finding: Rekognition `SearchFacesByImage` searches the largest face in an input image, so group frames must first be detected and cropped into one search image per person.
- Chose server-side household authorization records instead of trusting Android or using Cognito groups as the sole tenant/role source.
- Chose fixed S3 object tags/lifecycle for 30-day photos and application filtering plus DynamoDB TTL for one-year logs; TTL is asynchronous and not treated as exact access control.
- Added explicit API contracts, data models, file structure, data lifecycle, risk mitigations, verification checkpoints, and demo fallbacks.
- Spec deepening rounds: 1 architecture self-review focused on multi-face correctness, Ring staging access, Lambda CV packaging, authorization scope, exact retention behavior, and cost controls.
- Active shaping moment: Thomas asked Codex to use its best recommendations rather than selecting technologies individually, allowing the architecture to optimize for hackathon reliability and future adapter replacement.

## Build Checklist

- Thomas handed checklist design to Codex and selected the recommended autonomous mode with occasional visual verification pauses.
- Locked the primary wow moment: a Ring group visit becomes a count-aware alert, separate identity cards, an owner-approved profile update, an immutable audit entry, and searchable shared history.
- Selected focused commits after every checklist item and known-good checkpoints after items 4, 6, 10, and 11.
- Sequenced the highest-risk foundations before polish: multi-person domain and deterministic flow first, Android proof next, official Ring integration before AWS deployment, then Rekognition/Cognito/FCM integration.
- Encoded four participant checkpoints while keeping normal work autonomous.
- Kept cloud deployment as a distinct item so its validation and external-state confirmation are explicit.
- Consolidated the complete implementation into 12 ordered items, including the mandatory Devpost handoff.
- Checklist deepening rounds: not applicable on the handoff path; the finished checklist is presented for Thomas's gut-check before build mode locks.
- Active shaping moment: Thomas delegated both sequencing and checkpoint cadence by accepting Codex's recommendations.

## Build Execution

### Item 1 — Stabilize the existing foundation and quality gate

- Created branch `codex/knock-knock-mvp` from the repository's initial `master` branch.
- Created an isolated `.venv` and installed the existing `dev` dependency group.
- Verified the initial scaffold before feature work: 8 pytest tests passed, Ruff passed, and strict mypy passed across 32 source files.
- Confirmed local startup paths use simulator/stub adapters and require no Ring or AWS credentials.
- Confirmed `.gitignore` excludes credentials, token files, biometric datasets, private media, runtime logs, databases, Android packages, and build outputs.
- Environment note: verification ran on Python 3.14.6; the project remains compatible with its declared Python 3.12+ range. Third-party deprecation warnings were recorded but did not affect the clean baseline.

### Item 2 — Implement the multi-person domain and trust policies

- Added framework-independent household, membership, visit, visit-person, familiar-profile, proposal, media, and audit models while preserving the initial adapter contracts.
- Added injected-time policy functions for the 30-day learning period, 30-day unsaved-photo expiry, one-year visit retention, confidence bands, generic versus qualified alerts, fixed owner/member permissions, and conflict suppression.
- Verified independent review state for each person in a group visit, explicit face-undetected handling, owner approval requirements, and the age-13 affirmation gate.
- Verification: 17 pytest tests passed, Ruff passed, and strict mypy passed across 33 source files.

### Item 3 — Build append-only audit, retention, and local repositories

- Added an atomic JSON metadata repository for households, memberships, visits, independently reviewed people, familiar profiles, approval proposals, media, device tokens, and immutable audit events.
- Added optimistic version checks for concurrent visit, person-review, and proposal updates plus idempotent visit creation by Ring request ID.
- Enforced the retention boundary in reads: unsaved photo metadata becomes unavailable at 30 days, saved media remains available, and the associated text visit remains visible for its one-year window.
- Removed the legacy profile hard-delete route and changed the legacy repository boundary to reversible disabling; the shared repository exposes no profile, visit, or audit hard-delete method.
- Verified that member removal revokes active membership without erasing attributed audit history and that duplicate audit IDs cannot rewrite prior events.
- Verification: 23 pytest tests passed, Ruff passed, and strict mypy passed across 34 source files.

### Item 4 — Deliver the deterministic local API workflow

- Added a swappable multi-face vision port and a deterministic adapter backed by a sanitized, media-free three-person fixture manifest.
- Split the new FastAPI surface into demo, visits, profiles/proposals, audit, and device-token routers with safe service error envelopes and development-only fixture ingestion.
- Added fake owner/member authorization with the same role policy as the planned Cognito path. A member can propose a familiar profile but receives `403 forbidden` when attempting approval; the owner can approve it.
- Added independent person review, owner proposal decisions, state/profile/category/saved filtering with bounded offset pagination, media saving, familiar-profile queries, FCM token fingerprinting, and append-only audit retrieval.
- Added `scripts/run_local_demo.py`, which executes fixture ingestion -> three person cards -> member proposal -> denied member approval -> owner approval -> saved media -> audit history without Ring or AWS credentials.
- Concrete result: the fixture returned a generic `Visitor detected / 3 people detected` alert; person 1 was a high-confidence advisory suggestion, person 2 became an owner-approved `Taylor` profile, and person 3 remained explicitly `face_undetected`.
- Verification: the required unit/contract/e2e subset passed 18 tests; the full suite passed 26 tests; Ruff passed; strict mypy passed across 45 source files; `/docs` returned 200; the local demo script completed successfully without exposing storage paths or raw device tokens.

### Item 5 — Create the native Android foundation and offline timeline

- Generated a native multi-module Kotlin/Jetpack Compose application with `app`, `core:model`, `core:network`, `core:database`, `core:ui`, and `feature:timeline` boundaries.
- Added a Material 3 visual identity, Compose navigation, manual dependency injection, a Cognito-compatible session boundary, Retrofit/OkHttp networking with redacted authentication headers, Room persistence, and WorkManager refresh scheduling.
- Added an explicit 30-day learning-mode explanation, generic-alert language, offline status, searchable filter chips, an empty-state demo action, and visit cards that show person count, review status, saved-photo state, possible matches, and the expired-photo/retained-log boundary.
- The sanitized three-person offline fixture persists in Room and remains available when the local FastAPI service is unreachable; no Ring or AWS service credentials are stored on the device.
- Visual verification on the `Pixel_5` Google APIs emulator covered the empty state, loaded offline fixture, `Unknown` filter, multi-person summary, and expired-photo placeholder.
- Verification: `lintDebug`, `testDebugUnitTest`, and `assembleDebug` completed successfully (286 Gradle tasks); the debug APK installed and launched successfully on the emulator.

### Item 6 — Build Android review, profile approval, audit, and alert UX

- Added a dedicated review feature with one actionable card per detected person, explicit unknown and face-undetected outcomes, saved-photo control, existing-profile lookup, confidence language, and member-submitted familiar-profile proposals.
- Added a Room-backed owner approval queue and immutable modification history. The demo role switch proves that a household member can propose `Alex` but cannot decide it; the Ring owner can approve it, creating a familiar profile, updating the person record, and appending an attributed approval event.
- Upgraded the Room cache from schema 1 to 2 with profile, proposal, and append-only audit tables plus a validated `MIGRATION_1_2`; direct demo deep links seed missing data without overwriting prior review decisions.
- Added a replaceable visitor-notification gateway and future FCM message boundary. The local injector uses the same generic learning-period trust policy as the backend, and `knockknock://visits/{visitId}` opens the correct cached group visit.
- Added JVM tests for learning-period and post-learning alert copy, role permissions, and deep-link parsing; added an on-device Room migration test and Compose launch test.
- Manual emulator walkthrough: opened the three-person visit from a deep link, submitted `Alex` as a member, observed the member approval restriction, switched to Ring owner, approved the proposal, verified proposer/decision-maker audit entries, generated `Visitor detected / 3 people detected`, and tapped the notification back into the correct visit.
- Verification: the combined `lintDebug`, `testDebugUnitTest`, `assembleDebug`, and `connectedDebugAndroidTest` gate passed 516 Gradle tasks, including the Room migration and Compose UI tests on the Pixel 5 Google APIs emulator.

### Item 7 — Complete and validate the official Ring integration

- Added a per-account OAuth token-store boundary, refresh-token rotation, expiry/skew handling, and
  typed authentication/rate-limit failures. The local in-memory implementation is explicitly
  development-only; the AWS checkpoint will supply encrypted persistent storage.
- Completed official snapshot and historical-clip retrieval with multi-camera component selection,
  bounded duration/bytes, trusted HTTPS redirect hosts, partial-content support, retry/backoff for
  `429` and transient `5xx` responses, and typed unavailable-media errors.
- Added sanitized official v1.1 motion and button fixtures plus a raw-body HMAC replay script.
  Contract tests prove signature verification occurs before JSON parsing, duplicate request IDs are
  acknowledged without reprocessing, and accepted webhooks return within Ring's five-second limit.
- Added watermark-aware media tests that return synthetic marked bytes unchanged for snapshots and
  clips. No production code removes or obscures the Ring watermark.
- Live Playground/staging validation remains externally blocked because client credentials, HMAC
  key, a linked test account, and a Playground token are not present in the local environment. The
  sanitized official payload contract is green and the exact blocker is recorded in
  `docs/friction-log.md`.
- Verification: the full backend suite passed 41 tests; Ruff passed; strict mypy passed across 45
  source files; `git diff --check` passed.

### Item 8 — AWS serverless stack (local gate complete; live gate deferred)

- Added a SAM stack for HTTP API, FastAPI/Mangum Lambda, SQS/DLQ, an image-based worker Lambda,
  on-demand DynamoDB tables with TTL, private SSE-KMS S3 with fixed tagged lifecycle expiration,
  Cognito, Secrets Manager, short-retention logs, alarms, and separate least-privilege API/worker
  roles. No NAT Gateway or always-on service is present.
- Added a Python 3.12 Lambda API image, worker image/partial-batch entrypoint, bounded concurrency,
  example SAM configuration, cost-aware deployment/teardown runbook, and structural policy tests.
- `sam validate --lint` reports a valid template. `sam build` built both images, and
  `sam local start-api` returned HTTP 200 from `/health` with
  `ring-partner-api` and `aws-rekognition` selected.
- Installed a verified Amazon-signed AWS CLI v2.37.6 into the ignored project tool area and used
  AWS browser login with short-lived credentials. STS confirmed account `737272118136`, root
  identity, and the intended `us-east-1` deployment region before the authorized cloud attempt.
- Rebuilt both Lambda images successfully after starting Docker Desktop's existing Windows/WSL2
  services. The packaged artifacts remain under ignored `.tools/` paths.
- The authorized `sam deploy` stopped during SAM's managed-resource bootstrap with AWS
  `OptInRequired: The AWS Access Key Id needs a subscription for the service`. CloudFormation also
  rejected a read-only stack listing with the same account-activation error, so the Knock Knock
  application stack was not created and no live endpoint exists yet.
- Thomas approved the fallback: close item 8 on its validated local infrastructure gate and move
  live deployment, CloudFormation output inspection, billing/free-tier inspection, and smoke testing
  into item 10's existing end-to-end checkpoint. This preserves the architecture and avoids blocking
  independent Rekognition worker development while AWS billing activation completes.

### Item 9 — Multi-face Rekognition worker and learning loop

- Added bounded OpenCV image/video frame sampling and normalized per-face cropping to the worker
  image. The worker limits frames, faces per frame, crops per person, clip bytes, and adjacent-frame
  tracking work so a long or crowded Ring clip cannot create unbounded processing.
- Extended the swappable vision boundary with face detection, frame sampling, and cropping ports.
  The AWS adapter now calls `DetectFaces` for each sampled frame and `SearchFacesByImage` only on an
  individual crop, avoiding Rekognition's largest-face behavior on group images.
- Added cross-frame person tracking, duplicate-crop suppression, per-person evidence aggregation,
  quality thresholds, confidence bands, disputed-match suppression, and stable independent person
  results for a synthetic three-person visit.
- Added encrypted, household-scoped S3 media loading and 30-day tagged crop persistence. Added an
  owner-approval learning service that deduplicates examples, calls `IndexFaces`, increments profile
  versions, and places conflicting profiles under review instead of silently relearning them.
- Upgraded the SQS entrypoint to isolate records and return Lambda partial batch failures, preserving
  failed messages for retry and the existing DLQ/alarm path. Failure logs include the SQS message ID
  but no media bytes, credential values, or face images.
- Verification: AWS adapters passed against stub clients; the worker and learning tests covered three
  people, low-confidence/suppressed identity behavior, approved enrollment, conflicts, encrypted S3
  persistence, bounded work, and partial batch failures. The full backend suite passed 55 tests; Ruff passed; strict
  mypy passed across 53 source files; `git diff --check` passed; and SAM rebuilt both Lambda images,
  including the worker's boto3, NumPy, and headless OpenCV dependencies.
- The one live Rekognition invocation and CloudWatch log inspection remain combined with item 10's
  deployment checkpoint because AWS account service activation is still the known external gate.

### Item 10 — Cloud access and notifications (in progress; activation blocked)

- Added an API Gateway/Cognito identity adapter that accepts only claims already validated by the
  configured JWT authorizer and refuses caller-supplied headers as an identity source.
- Added server-side household authorization for active membership, sole-owner operations,
  invitation acceptance with a mandatory age-13 affirmation, member removal, and immediate access
  revocation without deleting historical records.
- Added an FCM HTTP v1 adapter with short-lived OAuth bearer injection, duplicate-token suppression,
  safe text/data payloads, visit deep links, and explicit retryable delivery failures so a failed
  push cannot be mistaken for a lost visit.
- Focused tests pass for validated Cognito claims, the owner/member authorization matrix, age
  affirmation, removal revocation, safe FCM payloads, and transient FCM failures. Ruff and strict
  mypy also pass for this increment.
- Refreshed AWS browser authentication successfully for account `737272118136` and installed the
  user-approved AWS skills/MCP configuration. STS succeeds, but CloudFormation still returns
  `OptInRequired: The AWS Access Key Id needs a subscription for the service`. Item 10 remains
  unchecked until AWS billing/service activation permits deployment, Cognito test users, a real
  FCM alert, CloudWatch inspection, and the participant checkpoint.

### Item 11 — Hardening and rehearsal (independent work in progress)

- Preserved item 10's MFA-gated live deployment checkpoint while Thomas was away from the
  authenticator device, and advanced only work that does not claim live AWS verification.
- Added least-privilege GitHub Actions gates for Python 3.12 Ruff, strict mypy, all backend tests,
  Android lint/unit/build, and rejection of common tracked credentials, biometric configuration,
  private logs/databases, and Android packages.
- Added a private vulnerability-reporting policy, repository threat model, and explicit privacy and
  fixed-retention inventory. The documents separate current controls from the evidence still
  required after deployment and from the legal/product work required before any public pilot.
- Added a timed three-path demo rehearsal runbook: live Ring/AWS, signed official-payload replay
  against AWS, and deterministic local fallback. Every path requires honest labeling and synthetic
  or consented media.
- Refreshed README quality/security guidance to reflect the implemented Cognito validated-claims
  boundary and server-side household authorization.
- Verification: Ruff passed; strict mypy passed across 57 source files; all 60 backend tests passed;
  `git diff --check` and the tracked-private-artifact filename check passed; Android
  `lintDebug`, `testDebugUnitTest`, and `assembleDebug` completed successfully across 334 tasks.
- Item 11 remains open until the live item 10 path is resolved, remaining cloud evidence is
  collected, dependency/security and clean-checkout gates run, and Thomas completes the encoded
  final visual/timed rehearsal checkpoint.
- The first remote CI run passed the backend job but exposed a runner-only Android setup issue:
  the setup action requested Google's retired `tools` SDK package. Updated CI to request only
  `platform-tools` and upgraded the maintained checkout/Java actions before re-running the gate.

