# Build Checklist

## Build Preferences

- **Plan ownership:** Codex designs and maintains the sequence; Thomas reviews outcomes and makes product decisions when a checkpoint exposes a real tradeoff.
- **Build mode:** Autonomous. This choice locks when checklist execution begins.
- **Comprehension checks:** N/A; Thomas is acting as product owner while Codex implements.
- **Git:** Create a `codex/knock-knock-mvp` branch before implementation. Make a focused commit after every completed checklist item, with an additional known-good tag or checkpoint commit after items 4, 6, 10, and 11. Never include credentials, real Ring media, face datasets, or local logs.
- **Verification:** Enabled. Run automated checks on every item and pause for a short participant-facing visual/manual review after items 4, 6, 10, and 11.
- **Check-in cadence:** Balanced autonomous build. Continue without re-asking between ordinary items; pause only at the encoded checkpoints, before a consequential cloud deployment if authorization is not already current, or when the checklist must materially change.
- **Primary wow moment:** A Ring group visit becomes a count-aware generic alert, separate AI-assisted identity cards, an owner-approved profile update with an immutable audit entry, and a searchable shared history.
- **Deadline guardrail:** Code-complete by October 16, reliability/testing by October 20, demo and documentation October 21, target submission October 22, emergency buffer October 23.

## Checklist

- [x] **1. Stabilize the existing foundation and quality gate**
  Spec ref: `spec.md > Overview`, `spec.md > File Structure`, `spec.md > Verification Checkpoints`
  What to build: Preserve the current ports-and-adapters scaffold, reorganize tests into the specified unit/contract structure where useful, add the missing development/runtime dependencies needed by the chosen architecture, and establish repeatable Ruff, mypy, pytest, and secret-safe configuration checks. Record the baseline in the README and build notes instead of rewriting working modules.
  Acceptance: The existing simulator webhook, profile, visitor, and adapter tests still pass; local startup requires no real Ring/AWS credentials; `.gitignore` excludes all documented secrets and private media; the selected adapter names appear in health output.
  Verify: Run `python -m ruff check .`, `python -m mypy src`, `python -m pytest`, and a FastAPI `GET /health` smoke test with simulator/stub settings.

- [x] **2. Implement the multi-person domain and trust policies**
  Spec ref: `spec.md > Data Model`, `spec.md > AI Usage`, `spec.md > Components And Responsibilities > Review and learning services`
  What to build: Expand pure domain models for household, membership, visit, visit-person, profile proposal, media metadata, and audit events. Implement injected-clock policies for the 30-day learning period, confidence bands, generic-versus-qualified alert text, one-year visit visibility, fixed roles, and conflict suppression. Replace single-visitor assumptions without importing AWS, Ring, FastAPI, or Android into the domain.
  Acceptance: A three-person visit retains three independent review states; day 1 alerts never contain names; day 31 high-confidence results use `Possible match`; low confidence and disputed profiles remain generic; member profile changes require owner approval; age affirmation and fixed-retention rules are enforced.
  Verify: Run focused unit tests for policy boundary dates, threshold edges, role matrix, face-undetected outcomes, multi-person grouping, and conflicting edits, then run the full Python suite.

- [x] **3. Build append-only audit, retention, and local repositories**
  Spec ref: `spec.md > DynamoDB Access Plan`, `spec.md > Data Flow > C. Retention`, `spec.md > Components And Responsibilities > Audit repository`
  What to build: Extend repository ports and local adapters for households, memberships, visits, people, profiles, proposals, media, device tokens, event ledger, and append-only audit history. Implement optimistic versions, one-year query filtering, 30-day unsaved-media metadata, saved-media state, and immutable audit interfaces. Remove or suppress hard-delete behavior that conflicts with the approved MVP.
  Acceptance: Expired unsaved media is unavailable while its one-year text visit remains; saved media remains marked available; audit rows cannot be updated or deleted through service ports; removed members lose access but their historical actions remain; concurrent review versions fail safely.
  Verify: Run repository tests using a temporary directory/database and injected clock; assert that no service route or repository interface exposes profile/audit hard deletion; run the full Python suite.

- [x] **4. Deliver the deterministic local API workflow**
  Spec ref: `spec.md > API Contracts`, `spec.md > Data Flow > A. Ring event to shared alert`, `prd.md > Epic 2`, `prd.md > Epic 4`, `prd.md > Epic 7`
  What to build: Split FastAPI routers by concern, add safe error envelopes, pagination/filter contracts, demo fixture ingestion, household/member authorization fakes, per-person review, owner approval, media-save, profile, audit, and FCM-token contracts. Use a deterministic multi-face adapter and sanitized fixture manifest to complete simulator event -> three person cards -> review proposal -> approval -> history/audit locally.
  Acceptance: Duplicate event delivery creates one visit; one fixture produces three linked people; member correction produces a pending proposal; owner approval changes shared state and appends an audit event; filters return familiar, unknown, face-undetected, unresolved, and saved states; no API exposes secrets or raw private paths.
  Verify: Run `python -m pytest tests/unit tests/contract tests/e2e`; open `/docs`; execute the scripted local demo flow and inspect its JSON responses. **Checkpoint:** show Thomas the local API workflow summary and one concrete three-person visit result before continuing.

- [x] **5. Create the native Android foundation and offline timeline**
  Spec ref: `spec.md > Decisions > Client`, `spec.md > File Structure`, `spec.md > Components And Responsibilities > Android application`
  What to build: Generate the Kotlin/Jetpack Compose Android project and the specified core/feature module boundaries at a practical MVP granularity. Add Material 3 theme, navigation, dependency injection, Retrofit client, Cognito-compatible session abstraction, Room cache, repository layer, learning-period banner, timeline, filters, empty/offline/error states, and fixture/local API configuration. Keep all Ring and AWS service credentials off-device.
  Acceptance: The app launches on a Google APIs emulator; a new household sees the learning explanation and demo action; fixture visits persist across restart in Room; the timeline shows person count, labels, verification state, media availability, and photo-expired placeholder; offline mode is visibly labeled.
  Verify: Run `apps\android\gradlew.bat lintDebug testDebugUnitTest assembleDebug`; launch the debug APK on an emulator and visually inspect empty, populated, filtered, offline, and expired-photo states.

- [x] **6. Build Android review, profile approval, audit, and alert UX**
  Spec ref: `prd.md > Epic 3`, `prd.md > Epic 4`, `prd.md > Epic 6`, `prd.md > Epic 9`, `spec.md > Demo And Submission Flow > Live demo path`
  What to build: Add the visit-detail screen with one card per detected person, existing-profile search, unknown/face-undetected decisions, new/corrected profile proposals, owner approval queue, profile detail, immutable modification history, saved-photo action, learning and confidence language, and notification deep links. Add FCM service abstractions and a local notification injection path; longer refresh work runs through WorkManager.
  Acceptance: A group visit can be reviewed person by person; members cannot directly apply canonical profile changes; owner approval updates all cached views; audit history shows proposer, decision maker, action, and time; generic and qualified alert copy follows policy; tapping a test notification opens the correct visit.
  Verify: Run Android unit, lint, Compose UI, Room migration, and deep-link tests; manually walk the group-review and approval flow on an emulator. **Checkpoint:** Thomas reviews the actual Android screens and confirms the core workflow is understandable before cloud integration.

- [ ] **7. Complete and validate the official Ring integration**
  Spec ref: `spec.md > Components And Responsibilities > Ring camera adapter`, `spec.md > External APIs And Dependencies > Ring`, `spec.md > Risks And Verification > Risk 1`
  What to build: Complete official Ring OAuth token refresh/storage boundary, JSON:API event normalization, raw-body HMAC verification, five-second acknowledgement, request-id idempotency, snapshot and bounded clip retrieval, typed rate-limit/token/media errors, watermark-aware fixtures, and Playground/staging replay tooling. Keep private API/session-cookie libraries out of the production path.
  Acceptance: Motion and button events normalize correctly; invalid signatures fail before body logging/parsing; duplicates return success without reprocessing; retry/backoff handles 429/5xx; snapshots/clips retain the Ring watermark; the Developers Playground or a sanitized official payload reaches the local/deployed contract.
  Verify: Run Ring contract tests and a timed webhook test; use the Ring Developers Playground where available to exercise device/media endpoints and capture non-secret friction notes. If staging credentials are incomplete, verify the replay adapter and record the exact external blocker without changing architecture.

- [ ] **8. Define and deploy the minimal AWS serverless stack**
  Spec ref: `spec.md > Decisions > Deployment`, `spec.md > Architecture`, `spec.md > Security And Privacy`, `spec.md > Local And Cloud Environments > AWS development stack`
  What to build: Add AWS SAM for API Gateway, FastAPI/Mangum Lambda, SQS/DLQ, worker Lambda container, DynamoDB on-demand tables/indexes/TTL, private SSE-KMS S3 with fixed lifecycle tags, Cognito user pool, Secrets Manager references, log retention, alarms, and split least-privilege IAM roles. Add explicit parameters and teardown/runbook commands; do not create a NAT Gateway or always-on service.
  Acceptance: Template validation finds no public S3 access or wildcard data-plane permissions; queues and Lambda timeouts satisfy retry guidance; lifecycle/TTL are configured; secrets are referenced rather than embedded; deployed health endpoint works; the existing $0.01 and $10 account budgets remain the cost backstop.
  Verify: Run `sam validate --lint`, `sam build`, policy/static checks, and template tests. Before the first cloud mutation, use the current user authorization/required confirmation; then run `sam deploy --guided`, smoke-test health, and inspect CloudFormation outputs and AWS Billing/Free Tier indicators.

- [ ] **9. Implement the multi-face Rekognition worker and learning loop**
  Spec ref: `spec.md > Media And Multi-Face Processing`, `spec.md > AI Usage > Recognition flow`, `spec.md > Risks And Verification > Risk 2`, `spec.md > Risks And Verification > Risk 3`
  What to build: Add bounded clip frame sampling in the worker image, Rekognition DetectFaces, per-face cropping, adjacent-frame deduplication, per-crop SearchFacesByImage, cross-frame aggregation, quality/confidence policy, S3 media persistence, IndexFaces enrollment after owner approval, conflicted-profile suppression, SQS partial batch failure handling, and DLQ visibility. Never search one group frame as if all faces were evaluated.
  Acceptance: A consented/synthetic three-person fixture creates three stable person records; multiple approved frames enrich a profile; low confidence remains unknown; correction produces learning feedback and audit history; watermark fixtures are supported; worker errors leave a visible retry/failure state instead of losing the visit.
  Verify: Run Rekognition adapter tests with stubbed AWS responses, worker container unit/integration tests, a bounded performance test, and one live development-stack recognition test using approved demo media; inspect CloudWatch logs for IDs only, not raw media or secrets.

- [ ] **10. Connect Cognito, household authorization, FCM, and Android to AWS**
  Spec ref: `spec.md > Components And Responsibilities > Household authorization service`, `spec.md > Components And Responsibilities > Notification service`, `spec.md > API Contracts > Household and devices`
  What to build: Implement Cognito sign-in/invitation acceptance, 13+ affirmation, server-side membership resolution, sole-owner authorization, member removal, Android token handling, FCM registration and HTTP v1 delivery, WorkManager refresh, Retrofit production configuration, Room synchronization, and visit deep links. Create only the owner and one member demo accounts required for acceptance testing.
  Acceptance: Members cannot invite/remove users or approve profiles; owner can; removing a member blocks future access without removing audit rows; cross-household/object requests fail; learning-period and low-confidence notifications are generic; a qualified post-learning notification uses `Possible match`; failed FCM delivery does not lose the visit.
  Verify: Run authorization matrix and JWT tests, Android sync/deep-link tests, FCM payload tests, and a device/emulator end-to-end event. **Checkpoint:** Thomas reviews the deployed Ring/AWS/Android path, receives a real test alert, and confirms the group visit opens correctly.

- [ ] **11. Harden, test, and rehearse the complete MVP**
  Spec ref: `spec.md > Testing Strategy`, `spec.md > Risks And Verification`, `spec.md > Verification Checkpoints`, `prd.md > Submission Proof Points`
  What to build: Finish security/threat-model/privacy/runbook documents, accessibility polish, structured metrics, retry/error states, retention reconciliation, test fixtures, README setup, CI, cost/teardown checks, and the full end-to-end acceptance suite. Rehearse all three demo fallback paths and create a sub-three-minute shot/script plan centered on the wow moment.
  Acceptance: Every PRD proof point has evidence; all automated suites pass; no credentials/private media are tracked; Ring/AWS paths are visible in code and demo; the app honestly shows uncertainty; retention and role boundaries are verified; a clean checkout can follow the README; fallback demo works if Ring or network access fails.
  Verify: Run the full Python and Android quality suites, `sam validate --lint`, secret scanning, dependency/security checks, a clean-environment smoke build, and the timed end-to-end demo rehearsal. **Checkpoint:** Thomas performs the final visual walkthrough and confirms the MVP story before submission assets are prepared.

- [ ] **12. Prepare Devpost handoff**
  Spec ref: `prd.md > Submission Proof Points`, `spec.md > Demo And Submission Flow > Submission evidence`
  What to build: Gather the final project story, architecture summary, AWS service list, Ring integration proof, screenshots, public/reviewer-accessible repository link, setup/testing instructions, under-three-minute video plan or URL, product feedback for every tool/API/SDK, feature requests, and the concrete friction log. Record what was created during the hackathon and whether the AWS Builder and Open Source mini challenges are being entered.
  Acceptance: The repository contains all source, assets permitted for sharing, license decision, and instructions needed for judging; private-repository reviewer access requirements are documented for action near submission; every required Devpost answer has a draft; the participant has enough verified material to run `$prepare-submission` without reconstructing the build history.
  Verify: Review the handoff materials against the live Devpost submission requirements, confirm links and video playback, verify no sensitive data is included, and confirm the next command is `$prepare-submission`.

## Checkpoints Summary

- **After item 4:** Local deterministic backend and three-person API workflow.
- **After item 6:** Native Android timeline, review, approval, audit, and notification UX.
- **After item 10:** Deployed Ring/AWS/Android end-to-end path and real test alert.
- **After item 11:** Final hardened MVP and timed demo rehearsal.

If an external dependency blocks Ring or AWS, preserve the completed adapter boundary, use the specified fallback for the next independent item, and revise the checklist only when the architecture or acceptance criteria must materially change.
