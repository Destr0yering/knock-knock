# Knock Knock

> **Know who's at the door before the knock knock!**

Knock Knock is a privacy-conscious visitor-awareness foundation for homes and businesses. A Ring
motion or doorbell event yields a freeze frame, a swappable vision engine suggests a familiar
profile or `unknown`, and the user remains responsible for confirming, correcting, categorizing,
or deleting the result.

This repository is a proof-of-concept foundation, not an access-control or safety system. Never
unlock a door, deny access, contact law enforcement, or make another consequential decision from a
face match alone.

## Architecture

The core application depends only on ports (interfaces):

```text
Ring webhook / simulator
        |
        v
CameraAdapter -> EventQueue -> VisitorPipeline -> FaceIdEngine
                                      |              |-- OpenCV LBPH (local)
                                      |              `-- AWS Rekognition (cloud)
                                      v
                           ProfileRepository + VisitorRepository
                                      |
                                      v
                                 AlertPublisher
                                      |
                              Android/API clients
```

- **Camera interface:** verifies Ring webhooks, normalizes motion/button events, and fetches media.
- **Vision engine:** accepts bytes and returns a suggested profile or `unknown`; local, AWS, and
  deterministic stub implementations share one interface.
- **User/alert interface:** persists the review record and publishes an alert without depending on
  Ring or a particular recognition vendor.

See [docs/architecture.md](docs/architecture.md) for boundaries and the complete data lifecycle.

## Stack

- Python 3.12, FastAPI, `httpx`, and an in-process async queue for the service foundation.
- OpenCV contrib/LBPH for the local demonstration engine; AWS Rekognition is an optional adapter.
- YAML for local profile metadata and JSON Lines for the private visitor log.
- Kotlin/Jetpack Compose is the intended Android client stack; the client boundary is documented
  in `apps/android/` and deliberately contains no service credentials.

The queue and local repositories are adapters too. Replace them with SQS/Redis and an encrypted
database when moving beyond a single-process demonstration.

## Quick start

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,local-vision]"
Copy-Item .env.example .env
Copy-Item config\known_faces.example.yaml config\known_faces.yaml
python -m uvicorn knock_knock.api.main:app --reload
```

Then visit `http://127.0.0.1:8000/docs`. With `CAMERA_BACKEND=simulator`, place a private test
image at `data/simulator/door.jpg` and POST the sample event shown in the API documentation to
`/v1/webhooks/ring`.

Run quality checks:

```powershell
python -m ruff check .
python -m mypy src
python -m pytest
```

## Ring authentication and webhooks

Knock Knock targets the **official Ring Partner API** rather than asking a user for a Ring password.
Register the app in the [Amazon Developer Portal](https://developer.amazon.com/ring/console/apps),
implement Ring OAuth account linking, and keep the client secret, access/refresh tokens, and HMAC
key in a server-side secret store. The service base URL is `https://api.amazonvision.com`; the OAuth
token endpoint is `https://oauth.ring.com/oauth/token`.

Configure a public HTTPS webhook that routes to `/v1/webhooks/ring`. The adapter verifies the
`X-Signature: sha256=...` HMAC against the **raw request body**, deduplicates `meta.request_id`,
returns promptly, and processes the event on a worker. Image download uses Ring's documented
two-step flow: POST `/v1/devices/{device_id}/media/image/download`, then GET the time-limited URL
from the `303 Location` header. Current Ring media includes a mandatory visible watermark; the
recognition crop/dataset should be tested with that overlay present.

Official references:

- [Getting started with Ring Developer Experience](https://developer.amazon.com/docs/ring/get-started.html)
- [Ring API development guide](https://developer.amazon.com/docs/ring/develop.html)
- [Ring Partner API documentation](https://developer.amazon.com/docs/ring/api-documentation.html)
- [Amazon's Ring API hello-world sample](https://github.com/AmazonAppDev/ring-api-helloworld)

### About unofficial Ring libraries

Older prototypes often use the community `ring-doorbell` package and session cookies. This scaffold
does not. Password/2FA scraping and private endpoints are brittle, may stop working, and are not a
suitable production or hackathon submission path now that an official partner API exists. If an
unofficial experiment is unavoidable, implement it as another `CameraAdapter`, use a disposable test
account, never commit cookies or credentials, and review Ring's current terms before proceeding.

## Selecting a vision backend

Set `KNOCK_KNOCK_VISION_BACKEND` in `.env`:

- `opencv`: all face detection/matching runs locally. Reference images live under
  `data/faces/<profile-id>/` and never enter Git.
- `aws`: searches an AWS Rekognition collection. Install `.[aws]`, use the normal AWS credential
  chain outside this repository, and configure the collection ID.
- `stub`: always returns `unknown`; useful for API, queue, and UI work without biometric tooling.

Confidence is advisory. The threshold is configurable, and every suggested match is stored as
`pending_review` until a user confirms or corrects it.

## Privacy and responsible use

- Obtain informed consent before enrolling a person's face; provide access, correction, export,
  and deletion controls.
- Minimize retention. Store the event ID and decision when a full image is unnecessary.
- Encrypt biometric references, OAuth tokens, and visitor logs at rest in any deployed system.
- Separate household or business tenants and enforce authenticated, least-privilege API access.
- Respect Ring privacy zones and local biometric/privacy laws (for example BIPA, CCPA/CPRA, GDPR,
  and applicable workplace notice/consent rules). Get qualified legal advice for a real launch.
- Measure false-match behavior across lighting, angles, skin tones, eyewear, masks, and the Ring
  watermark. An `unknown` result is safer than a low-confidence name.

## API surface

- `GET /health` — liveness and selected adapter names.
- `POST /v1/webhooks/ring` — signed Ring webhook or local simulator event.
- `GET/POST /v1/profiles` — list/register profile metadata.
- `POST /v1/profiles/{profile_id}/enroll` — enroll uploaded reference images.
- `GET /v1/visitors` — list newest visit records for review.

Authentication for management routes is a required production hardening item; do not expose this
proof of concept directly to the internet except behind a private tunnel/access layer.

## Git initialization

This folder is already a Git worktree, so do not delete `.git`. For a new copy, the exact initial
sequence is:

```powershell
git init -b main
git add .
git status --short
git commit -m "chore: scaffold Knock Knock architecture"
```

If `git init` created `master` on an older Git version, run `git branch -M main` before committing.

## Contributing

1. Create a focused branch such as `codex/ring-webhook-retries`.
2. Keep vendor code in `adapters/`; application services must depend on `ports/` only.
3. Add tests for every normalization rule, recognition decision, and privacy-sensitive change.
4. Run Ruff, mypy, and pytest before opening a pull request.
5. Never attach real Ring media, face datasets, tokens, logs, or `.env` files to issues or commits.
6. Describe privacy impact, migration needs, and manual verification steps in the pull request.

