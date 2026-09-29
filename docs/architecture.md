# Knock Knock architecture

## Design rules

1. Domain models contain no Ring, OpenCV, AWS, FastAPI, or Android imports.
2. Application services import ports, never concrete adapters.
3. Adapters translate external shapes into domain models at the boundary.
4. A recognition result is a suggestion. Only a user action can make it `confirmed`.
5. Raw media and biometric references are private, optional, and governed by retention settings.

## Runtime lifecycle

1. Ring sends a signed `motion_detected` or `button_press` webhook.
2. The API verifies HMAC over the raw bytes and normalizes the event through `CameraAdapter`.
3. The idempotency ledger claims `meta.request_id`; duplicates return HTTP 200 without reprocessing.
4. The API places the normalized event on `EventQueue` and returns before the five-second deadline.
5. `PipelineWorker` asks the camera adapter for a snapshot at the event epoch timestamp.
6. `FaceIdEngine` returns a match suggestion only when it clears the configured threshold.
7. `VisitorPipeline` stores a `pending_review` visitor record and publishes an alert.
8. The Android client retrieves the record and lets the user confirm, correct, tag, or delete it.

## Adapter map

| Port | Included adapters | Next production adapter |
|---|---|---|
| `CameraAdapter` | Official Ring Partner API, simulator | Recorded-event replay fixture |
| `FaceIdEngine` | OpenCV LBPH, AWS Rekognition, unknown stub | Calibrated embedding model |
| `AlertPublisher` | Structured application log | Android push/ADM notification |
| `ProfileRepository` | Local YAML | Encrypted tenant-aware database |
| `VisitorRepository` | Local JSON Lines | Encrypted database with retention jobs |
| `EventQueue` | In-process `asyncio.Queue` | SQS, Redis Streams, or another durable queue |

## Failure boundaries

- **Invalid signature:** reject before JSON parsing or logging the body.
- **Duplicate delivery:** acknowledge but do not enqueue twice.
- **Expired token / 429 / 5xx:** the Ring adapter raises a typed boundary error; durable queue retry
  and OAuth refresh are the next deployment layer.
- **No face / low confidence:** store `unknown`, never guess the closest profile.
- **Worker failure:** log event/request IDs without raw media. A production queue must dead-letter.
- **Unavailable alert sink:** the visit log remains the source of truth.

