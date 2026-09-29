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

