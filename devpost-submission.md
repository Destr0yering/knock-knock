# Knock Knock

## One-line Summary

Know who's at the door before the knock knock: a privacy-conscious Android companion that turns Ring events into multi-person, user-verified visitor alerts and history.

## Tagline

**Know who's at the door before the knock knock!**

## Problem

A doorbell notification says that something happened, but households still have to open a live view, inspect several people at once, remember prior visits, and decide whether an automated identity suggestion deserves trust. Most familiar-face concepts also hide uncertainty and make group arrivals look like a single-person problem.

Families need a visitor-awareness tool that remembers context without turning a machine suggestion into an identity verdict. It should count everyone, handle unknown and face-undetected cases, let household members contribute, reserve canonical changes for the Ring account owner, and keep a clear record of how profiles changed.

## Solution

Knock Knock is an Android visitor-awareness application backed by the official Ring integration boundary and a modular AWS/Python service. A Ring motion or doorbell event enters a durable processing pipeline. The worker samples a bounded number of frames, detects every visible face, crops and tracks each person independently, and asks a swappable vision engine for advisory matches.

During the first 30 days, every notification stays generic while the household labels visits and gathers multiple owner-approved examples. Later, only high-confidence, conflict-free evidence can produce tentative language such as `Possible match: Morgan`. The user—not the model—remains the identity authority.

Each group visit becomes separate person cards for familiar, unknown, or face-undetected outcomes. Members may propose corrections; only the Ring account owner can approve canonical profile changes. Every modification produces immutable audit history. Unsaved photos expire after 30 days, explicitly saved photos remain available, and text visit history remains visible for one year.

## Why This Matters

Knock Knock goes beyond a basic motion alert by making Ring events useful for everyday household awareness and caretaking. A parent can understand who arrived together. A household can distinguish a recurring delivery pattern from an unknown visitor. A caregiver can review visits without relying on a brittle, overconfident identity label.

The same adapter-based foundation can later support small businesses, accessibility workflows, and carefully authorized door automation. The hackathon MVP deliberately excludes automatic unlocking, law-enforcement escalation, demographic inference, and any consequential action based on face recognition.

## How We Used AI

- AWS Rekognition is the production vision adapter for face detection, collection search, and owner-approved enrollment.
- Every group frame is detected and split into individual face crops before matching; the app never treats Rekognition's largest-face result as an evaluation of the whole group.
- Multiple crops are aggregated per tracked person across adjacent clip frames.
- Image quality, configurable similarity thresholds, conflict state, and the 30-day learning policy determine whether output remains unknown or becomes a tentative suggestion.
- Confirmations and corrections create learning evidence only after owner approval. Disputed profiles are suppressed rather than silently retrained.
- Deterministic synthetic fixtures reproduce the three-person workflow without private biometric data or cloud credentials.
- The system never infers emotion, intent, criminality, health, race, gender, or other sensitive attributes.

## How We Used Codex

Codex served as the implementation partner across product shaping, architecture, Android, backend, infrastructure, and testing. Thomas defined the product policies—especially the learning period, sole-owner administration, fixed retention, and immutable profile history—while Codex translated them into a ports-and-adapters architecture and focused Git commits.

Codex helped:

- Turn the initial idea into a scope, PRD, technical specification, and 12-item build checklist.
- Preserve swappable Ring, vision, storage, queue, and alert boundaries rather than coupling the product to one vendor implementation.
- Build and test the native Kotlin/Jetpack Compose Android timeline, review, approval, audit, offline cache, and notification deep-link experience.
- Implement official Ring OAuth/webhook/media contracts, multi-face Rekognition processing, S3 retention, SQS partial failures, Cognito claim boundaries, owner/member authorization, and FCM payloads.
- Run Ruff, strict mypy, pytest, Gradle lint/unit/instrumentation builds, SAM validation, Docker image builds, and emulator walkthroughs.
- Record integration friction honestly, including the current AWS `PENDING_ACTIVATION` deployment blocker, instead of fabricating live-cloud evidence.

No private Ring media, face dataset, credential, or conversation transcript is included in the repository or this entry.

## Key Features

- Official Ring motion/button event normalization, raw-body HMAC verification, quick acknowledgement, idempotency, and bounded media download
- Count-aware notifications for group visits
- Independent cards and review state for every detected person
- Explicit unknown and face-undetected outcomes
- Thirty-day generic-alert learning period
- Tentative post-learning matches only for high-confidence, conflict-free evidence
- Member proposals with sole-owner approval
- Continuous learning from multiple approved clip frames
- Immutable, attributable profile modification history
- Searchable Android timeline with familiar, unknown, unresolved, face-undetected, and saved filters
- Room-backed offline cache and visible offline/expired-photo states
- Notification deep links to the correct visit
- Fixed 30-day unsaved-photo and one-year text-log retention
- Modular deterministic, OpenCV, and AWS Rekognition vision adapters
- Retry-safe SQS worker behavior with DLQ visibility

## Architecture

```text
Ring API / Playground / sanitized simulator
                    |
                    v
          API Gateway HTTP API
                    |
             FastAPI Lambda
             /      |      \
      HMAC webhook  Cognito  OAuth callback
             |
             v
        SQS + DLQ  ---> Worker Lambda container
                         |       |        |
                  Rekognition    S3    DynamoDB
                         \       |       /
                          visit + audit state
                                  |
                              FCM alert
                                  |
                    Android + Room + Compose
```

The domain and services depend on ports. Ring, Rekognition, S3, FCM, local fixtures, OpenCV, and storage implementations are replaceable adapters. AWS SAM defines API Gateway, Lambda, SQS/DLQ, DynamoDB, private encrypted S3, Cognito, Secrets Manager, alarms, and split IAM roles without a NAT Gateway or always-on server.

## AWS Builder Mini Challenge

**Enter:** Yes.

Knock Knock documents and implements an AWS serverless integration using:

- API Gateway HTTP API for public Ring webhooks and authenticated Android APIs
- Lambda/Mangum for FastAPI and an image-based Lambda worker for bounded OpenCV processing
- SQS with partial batch failures and a DLQ for durable asynchronous Ring processing
- Rekognition `DetectFaces`, per-face `SearchFacesByImage`, and owner-approved `IndexFaces`
- Private SSE-KMS S3 media storage with controlled 30-day lifecycle tags
- DynamoDB on-demand tables, optimistic writes, indexes, and TTL cleanup
- Cognito User Pools for Android authentication, with server-side membership authorization
- Secrets Manager for Ring and Firebase credentials
- CloudWatch logs and alarms designed to contain identifiers, not media or secrets

The SAM stack validates and builds locally. Live deployment evidence remains pending because the newly created AWS account currently reports `PENDING_ACTIVATION`; this limitation will be updated before final entry.

## Open Source Mini Challenge

**Intended entry:** Yes, once the repository is published.

Knock Knock is a new project created during the hackathon window and licensed under MIT. The contribution is a modular, privacy-conscious reference implementation showing how to process group Ring events correctly: detect and crop every face before matching, keep identity advisory and user-verified, enforce owner/member roles server-side, and preserve a deterministic credential-free demo path.

- Contribution URL: **TODO — public GitHub repository or qualifying contribution URL**
- Project repository URL: **TODO — public GitHub URL**
- GitHub username: **TODO — confirm username**

## Testing Instructions

### Credential-free backend

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,local-vision]"
Copy-Item .env.example .env
Copy-Item config\known_faces.example.yaml config\known_faces.yaml
python -m ruff check .
python -m mypy src
python -m pytest
python scripts/run_local_demo.py
```

The demo produces one Ring-style three-person visit, proves a member cannot approve their own proposal, applies the owner's approval, saves one photo, and prints append-only audit event types.

### API exploration

```powershell
python -m uvicorn knock_knock.api.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. Use `X-Demo-User: demo-owner` or `demo-member` on development-only demo routes.

### Android

```powershell
cd apps\android
.\gradlew.bat lintDebug testDebugUnitTest assembleDebug
```

For the full instrumented gate, start a Google APIs emulator and run:

```powershell
.\gradlew.bat connectedDebugAndroidTest
```

### AWS infrastructure

Follow `docs/aws-deployment-runbook.md` to validate/build the SAM stack, confirm identity and region, deploy only after authorization, inspect outputs, smoke-test `/health`, and tear the development stack down.

## Public Demo Link

**TODO — optional deployed health/testing URL after AWS activation.**

The credential-free local demo and Android emulator path remain the documented fallback.

## Public Repository Link

**TODO — publish the repository after the pre-publication secret/privacy scan.**

## Demo Video

**TODO — public English YouTube or Vimeo URL; maximum 3 minutes.**

See `docs/demo-video-script.md` for the timed shot plan.

## Screenshot Shot List

1. Android learning-period timeline with the `Visitor detected / 3 people detected` result.
2. Visit detail showing three independent person cards: possible familiar person, unknown/proposed identity, and face undetected.
3. Member proposal followed by the Ring-owner-only approval queue.
4. Immutable profile modification history showing proposer, decision maker, action, and time.
5. Filtered history with an expired-photo placeholder and retained visitor log.
6. Optional architecture/SAM terminal proof showing successful tests and local image build without secrets.

## Product Feedback Draft

### Tools, APIs, and SDKs used and why

We used the Ring Partner API boundary for OAuth, webhook events, motion/button normalization, and snapshot/clip retrieval. We used Kotlin, Jetpack Compose, Material 3, Room, Retrofit/OkHttp, WorkManager, and the FCM client boundary for the Android experience. We used FastAPI, Pydantic, Mangum, boto3, OpenCV, and AWS SAM for the backend. AWS services include API Gateway, Lambda, SQS/DLQ, Rekognition, S3, DynamoDB, Cognito, Secrets Manager, KMS-backed encryption, SNS, and CloudWatch.

### What worked well

Ring's documented HMAC and request-ID semantics enabled a clean, retry-safe webhook boundary. Its simulator/Playground direction makes a physical device optional. SAM made the complete serverless architecture reviewable and locally buildable. Rekognition's face-detail and collection APIs fit a swappable vision adapter. Jetpack Compose, Room, and WorkManager supported a coherent offline-first Android workflow with durable refresh and testable UI state.

### What needs work

Ring snapshot and clip downloads use different successful response shapes, and multi-camera component selection is easy to overlook; one end-to-end media example would reduce mistakes. Rekognition documentation should emphasize more visibly that `SearchFacesByImage` searches the largest face, because group images require detection and per-face cropping first. The AWS new-account experience allowed STS login while CloudFormation still failed with `OptInRequired`; a console-visible activation state and clearer expected propagation time would make the blocker easier to diagnose.

### Onboarding experience

The local/simulator experience was productive once the official payload shapes and adapter boundaries were established. Android setup was straightforward with the installed SDK and Google APIs emulator. AWS local SAM validation was reproducible, but the account activation state blocked the first cloud deployment after payment verification. The friction log records the exact steps, expected behavior, actual errors, workarounds, and suggestions.

### Would we build with these services again?

Yes. Ring events plus AWS serverless services are a strong fit for event-driven visitor awareness, especially when processing is asynchronous and media work is bounded. We would retain the same ports-and-adapters design, deterministic fallback, explicit uncertainty, and server-side authorization. We would also begin AWS account activation earlier and validate Ring Playground credentials before the main integration sprint.

## Feature Requests

- **Critical:** Add a single official Ring sample that covers webhook receipt through snapshot and clip retrieval for both single- and multi-camera devices.
- **Important:** Surface AWS account activation state and remediation directly in CloudFormation/SAM errors and the console.
- **Important:** Add a Rekognition group-photo guide that explicitly demonstrates DetectFaces, individual crops, and one search per crop.
- **Nice-to-have:** Provide a Ring developer test fixture library containing watermark-aware, consent-safe group scenes and common error responses.

## Friction Log

Publish `docs/friction-log.md` with the repository and use its public GitHub URL for official field `28301`. It documents Ring media-contract friction, local SAM/Docker setup, and the AWS `PENDING_ACTIVATION` blocker with actionable suggestions.

## Submission Readiness Notes

Implemented and verified locally:

- Deterministic Ring-style three-person backend workflow
- Android timeline, filters, visit review, proposal/approval, audit, notification, Room migration, and deep link
- Official Ring request normalization, signature verification, idempotency, media boundaries, and sanitized replay fixtures
- Multi-face Rekognition adapter/service, bounded OpenCV worker image, S3 persistence, owner-approved learning, SQS partial failures
- Cognito claim boundary, household role enforcement, age affirmation, access revocation, and FCM HTTP v1 payload behavior
- Python, Android, SAM, Docker, and emulator verification recorded in `docs/hackathon-build/build-notes.md`

Still required before final submission:

- AWS account activation and live deployment/evidence
- Live Ring Playground or clearly filmed sanitized official simulator/replay path
- Public GitHub URL and GitHub username
- Screenshots and under-three-minute video URL
- Final security/secret scan and participant review
- Confirmation of official eligibility checkboxes

## Known Limitations

- The AWS account is currently `PENDING_ACTIVATION`, so live CloudFormation, Cognito, Rekognition, and FCM proof is not yet available.
- Ring Playground credentials and a linked staging account are not present locally; official sanitized replay fixtures cover the contract meanwhile.
- Recognition is advisory and not suitable for automatic unlocking, denial of entry, law-enforcement escalation, or another consequential decision.
- The MVP supports one household and two fixed roles rather than business multi-site administration.
- Private biometric calibration across diverse real-world conditions remains future validation work; repository fixtures are synthetic and contain no face dataset.

## TODO Official Form Fields

- `28285` Submitter Type: **Individual**
- `28286` Organization Name: **N/A**
- `28287` Country: **TODO — confirm country of residence**
- `28288` Canada province: **TODO — confirm N/A or province**
- `28289` Primary Track: **Ring**
- `28290` GitHub repository: **TODO**
- `28291` Project timing: **New** (first commit September 29, 2026)
- `28293` AWS Builder Mini Challenge: **Yes**
- `28294` AWS services and integration: use the AWS Builder section above, updated with live evidence
- `28295` Open Source Mini Challenge: **Yes, contingent on public MIT-licensed repository**
- `28296` Contribution URL: **TODO**
- `28297` Project repository URL: **TODO**
- `28298` GitHub username: **TODO**
- `28299` Open-source description: use the Open Source section above
- `28300` Feature Requests: use the Feature Requests section above
- `28301` Friction Log URL: **TODO — public URL to `docs/friction-log.md`**
- `28302` Project Testing Link: **TODO — README or public test evidence URL**
- `28303`–`28307` Feedback: use the five Product Feedback sections above
- `28308` Age: **TODO — participant must confirm**
- `28309` Eligible Jurisdiction: **TODO — participant must confirm**
- `28310` Employee status: **TODO — participant must confirm**

Official deadline: October 23, 2026 at 12:00 PM Pacific Time (19:00 UTC).
