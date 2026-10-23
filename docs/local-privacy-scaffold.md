# Knock Knock — original Step 1 scaffold and configuration

Implementation has since proceeded through Steps 2–5 at the owner's request.
See [current private Android build and testing](private-android-testing.md).
The scaffold discussion below records the initial module plan, not current
implementation status or a requirement to pause for further approval.

The owner selected Android-tablet processing and storage. Keep Kotlin/Compose
as the frontend, Room as the current database boundary, and Python/FastAPI for
synthetic API testing and future Ring control-plane work. No mandatory laptop
or Nano companion is introduced. Database encryption is implemented in Step 2;
the Step 1 scaffold does not encrypt the current Room/YAML/JSON repositories.

## Directory structure

```text
Knock Knock/
├── apps/android/
│   ├── app/                         existing Compose application
│   ├── core/
│   │   ├── camera/                  NEW: input and audio-free frame boundary
│   │   ├── vision/                  NEW: interchangeable local AI engines
│   │   ├── privacy/                 NEW: Keystore, encryption, access, retention
│   │   ├── evidence/                NEW: provenance and integrity exports
│   │   ├── model/                   existing domain types
│   │   ├── database/                existing Room boundary
│   │   ├── network/                 existing API adapter
│   │   └── ui/                      existing design components
│   └── feature/{timeline,review}/   existing screens
├── src/knock_knock/                 existing Python service
│   ├── ports/{camera,vision,...}.py
│   ├── adapters/                    Ring, simulator, legacy local/cloud engines
│   ├── services/
│   └── api/
├── config/privacy-mvp.toml          NEW: intended privacy requirements
├── .env.local.example              NEW: synthetic-only service environment
├── infra/local/Dockerfile          NEW: non-root synthetic test image
├── compose.local.yaml              NEW: loopback, ephemeral state, no runtime egress
├── scripts/dev.ps1                 NEW: unified check/test/serve entry point
├── tests/                          existing Python tests
├── fixtures/                       synthetic fixtures only
└── .runtime/                       ignored development records; never private media
```

Each new Android module includes its Gradle dependency file and manifest. The
modules are registered but intentionally not wired into the running app until
their implementations exist. No new database schema, API route, or screen is
introduced in Step 1. Existing API and UI tests are retained; new behavior tests
are added alongside the implementations in Steps 2–4, not as empty passing tests.

## Data placement and technical boundaries

Final private records and AI execution belong on the owner Android device.
Ring still requires its cloud for camera access. A minimal authorization/event
relay may hold Ring tokens and routing metadata; it must not persist profiles,
visitor images, identity references, or visit logs. Precise media transport and
availability while the tablet is asleep need verification during Ring integration.
No claim of completely offline Ring operation is made.

No audio is captured or retained by the intended app. Ring-origin MP4 files may
include audio: the implementation must decode visual frames without storing the
original container, and export silent derived media with transformation metadata.
No microphone permission alone cannot enforce that requirement.

Encryption must cover records, references, media, and temporary disk files. Keys
are held with Android Keystore, not in env files. System app backup remains
disabled; optional encrypted owner backup is a later feature. Retention targets
are 30 days for unsaved photos and 365 days for visit records. Saved photos may
be kept until owner deletion. Owner access, correction, deletion, and profile
modification history are part of Steps 2–4. An export hash detects changed bytes
relative to a manifest; it is not proof of a legally admissible record.

## Developer environment

Prerequisites: Python 3.12+, JDK 17+, installed Android SDK 35, and the existing
Gradle wrapper. Docker Desktop with its Linux engine is optional for Python tests.
No separate database container is needed for an Android-owned SQLite database;
on-device instrumentation tests exercise the actual database and Keystore later.

From the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\scripts\dev.ps1 -Mode Check
.\scripts\dev.ps1 -Mode Test
.\scripts\dev.ps1 -Mode Test -DeviceTests
.\scripts\dev.ps1 -Mode Serve
```

`Test` runs Python tests then Android unit tests. `-DeviceTests` additionally
requires an authorized tablet/emulator for instrumentation; `-BackendOnly` runs
only the Python suite. `Serve` starts the existing synthetic service at
`http://127.0.0.1:8000/docs` in the foreground. The script restores overridden
environment variables on exit. Do not import private media into this harness.

Optional isolated container commands (Docker engine must be running):

```powershell
docker compose -f compose.local.yaml config --quiet
docker compose -f compose.local.yaml --profile test run --build --rm backend-tests
docker compose -f compose.local.yaml up --build simulator
docker compose -f compose.local.yaml down
```

The container runs the existing simulator/stub stack. State is in a bounded
tmpfs and disappears when the container is removed. Its runtime network blocks
outbound traffic; image dependency installation requires network during build.
The host script uses the same synthetic config but is not network sandboxed.
Neither harness establishes encryption in the Android app.

## Review checkpoint

Step 1 creates configuration and module boundaries only. Step 2 will implement
the protected data model, encryption/key lifecycle, migrations, and synthetic
seed records. Step 3 implements local AI, input filtering, owner access, and
associated tests; Step 4 wires them into the screens; Step 5 validates the whole
flow and packages the test build. Pause for owner review after each step.
