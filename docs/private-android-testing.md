# Private Android MVP — build and testing

For checks actually performed and the outstanding device-test blocker, see
`private-android-validation.md`.

This implementation keeps imported visitor images, face references, labels, and
visit records on the owner Android device. It uses Kotlin/Compose, SQLCipher with
Room, Android Keystore, AES-GCM file encryption, and bundled OpenCV YuNet/SFace
models. Owner device-credential unlock gates access and re-locks on background
and after five minutes. Anyone with the device credential can unlock; the app
does not yet verify that this person owns a Ring account.

## Implemented flow

1. Unlock the tablet journal using its configured screen-lock credential.
2. Acknowledge the image-use notice and import a JPEG, PNG, or WebP still image.
3. The app decodes/resizes it in memory, detects usable faces, and stores JPEG
   crops and embeddings in encrypted local records. Original imported files
   remain wherever the owner selected them; the app does not delete those files.
4. Review every face. A sufficiently separated local similarity result may be
   shown as a possible match; it never confirms identity automatically. Save a
   named or anonymous profile, confirm an existing profile, or keep it unknown.
5. The owner can label a visit arrival/departure, correct identity/profile labels,
   delete records, keep photos, and adjust retention. Direction is owner-labelled,
   not inferred from a still image.
6. Export records only after approving a readable ZIP sharing notice. Its manifest
   includes available provenance, import/export timestamps, audit history, image
   transformations, and SHA-256 hashes of the exported JPEGs.

The current APK requests INTERNET for the separately configured Ring/cloud
integration and removes RECORD_AUDIO. The local image-import path uses bundled
models and encrypted local records. Network permission alone does not prove
that Ring linking or live event handling works; those paths remain unverified.
The synthetic Nebius demo stays separate from private records.

## Limits that matter when testing

- A working Ring connection has not been verified in this APK. Using Ring
  would still involve Ring's cloud; this version makes no fully offline Ring claim.
- Detected face counts do not establish the total number of people; obscured faces
  are not counted. Local matching thresholds are conservative prototype settings,
  not calibrated accuracy guarantees. No automatic door unlocking is included.
- The stored media are transformed face crops, not original camera recordings.
  Original capture time is unknown for imports. Export hashes do not establish
  original authenticity, a trusted clock, legal admissibility, or chain of custody.
- Normal storage is encrypted; owner-requested ZIP exports are readable. Export
  cache cleanup runs on launch and periodically after one hour (Android may delay
  background work). Apps selected for sharing can retain their own copies.
- Retention defaults: unsaved visit images 30 days, visit logs 365 days. Owner
  settings can change those windows. Retention is applied when the journal unlocks;
  an unused/locked tablet is not guaranteed to delete records at a wall-clock
  deadline. Kept visit photos remain until their visit is deleted/expired; profile
  reference images remain until the profile is deleted or its reference corrected.
- Device keys are Keystore-protected but not individually authentication-bound;
  the credential check is an application authorization gate. Keys/data cannot be
  recovered after key loss, uninstall, or device reset. Encrypted backup/recovery
  remains a later feature, with no remote backup enabled by default.

## Run checks with one command

Use PowerShell in the project root. Existing dependencies may already be present;
do not recreate a populated virtual environment unnecessarily.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\scripts\dev.ps1 -Mode Test
```

The unified command runs Python endpoint/worker tests and all Android JVM tests.
It uses a dedicated build-output folder in local Temp to avoid OneDrive resource
locking. JDK 17+, Android SDK 36, and the existing Gradle wrapper are required.
Android minSdk remains 26; targetSdk remains 35. The Python service is only a
synthetic harness, not production storage for Android identities.

For instrumented tests, authorize an emulator/tablet in Android tooling first:

```powershell
.\scripts\dev.ps1 -Mode Test -DeviceTests
```

Device tests cover the real Keystore vault, SQLCipher reopen/encrypted bytes,
migrations, owner gate, correction and retention, bundled local inference, export
hashes, and absence of network/audio permissions. Storage tests use separate
test-only database names; they do not erase the production private database.

To build an installable test APK with isolated generated output:

```powershell
$env:KNOCK_KNOCK_BUILD_ROOT = Join-Path $env:LOCALAPPDATA 'Temp\knock-knock-private-build'
Push-Location apps/android
.\gradlew.bat --no-daemon --max-workers=2 -I ../../scripts/gradle-isolated.init.gradle assembleDebug
Pop-Location
```

Output: `$env:KNOCK_KNOCK_BUILD_ROOT\app\outputs\apk\debug\app-debug.apk`.
Use a tablet with a screen-lock PIN/password. This is a debug build for testing,
not a production-signed Play Store release. Existing installer signatures must
match for an upgrade; never uninstall a private-data build to fix an update without
first considering loss of its device keys and records.

## Optional synthetic container

```powershell
docker compose -f compose.local.yaml config --quiet
docker compose -f compose.local.yaml --profile test run --build --rm backend-tests
docker compose -f compose.local.yaml up --build simulator
```

The same Python service/test image uses synthetic fixtures and ephemeral tmpfs
state. Its internal runtime network blocks outbound calls and exposes the service
only on host loopback. Docker Desktop must have its Linux engine running. Device
database behavior is verified on Android, not substituted by a server database.

## Contribution and Git review

Keep adapter/vision/storage/UI changes within their module boundaries. Include
behavior tests for identity uncertainty, data protection, and retention changes.
Never submit real visitor datasets, vaults, keys, credentials, or exports.

This workspace already has a Git repository and earlier uncommitted changes.
Review changes before staging. Do not reinitialize Git or stage all preexisting
changes blindly. Model licenses and immutable checksums are in
`apps/android/core/vision/src/main/assets/models/NOTICE.md`. Model weights are
bundled for the prototype; training-data provenance remains a commercial-release
review item.
