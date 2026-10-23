# Private Android MVP validation - October 5, 2026

## Outcome

The local image-import MVP and its instrumented test APKs build successfully.
This is a debug/testing build, not a production-ready release or a working Ring
integration. Android device validation remains outstanding.

## Checks actually performed

| Check | Result |
| --- | --- |
| Python synthetic API/worker suite | 62 passed; deprecation warnings remain |
| Android JVM unit suite | 14 passed, zero failures/errors across six suites |
| App debug APK assembly | Passed |
| App, database and privacy instrumented test APK assembly | Passed |
| Final expanded local-AI integration test compilation | Passed |
| APK signature verification with apksigner | Passed, APK Signature Scheme v2 |
| Packaged permissions inspected with aapt | No INTERNET or RECORD_AUDIO permission |
| Git whitespace check | Passed; existing LF/CRLF conversion warnings only |
| Local Docker Compose configuration | Validated; container execution not performed |

The Android unit suites cover export-cache cleanup, database mapping, trust policy,
authenticated encryption, similarity/ambiguity handling, and timeline filtering.
Python tests exercise the separate legacy prototype with mocks and synthetic
fixtures; they are not proof of live Ring access or Android storage protection.

## Device test blocker

The existing Pixel_5 Android 31 emulator could not be used. An initial boot stayed
offline under resource pressure and was shut down. A second launch, after removing
obsolete generated build outputs, terminated with:

```text
FATAL | Your device does not have enough disk space to run avd: Pixel_5.
```

C: had approximately 1.07 GiB free. No physical Android device was connected.
No emulator data, user source, or private visitor records were deleted. Two
obsolete generated app build directories were removed, freeing approximately
524 MiB; their contents can be recreated by rebuilding.

Therefore real bundled-model inference, Android Keystore/SQLCipher behavior,
storage migration/retention, UI interaction, and end-to-end export checks are
**compiled but not executed on an Android device**. Do not treat them as passed.
Docker Desktop's engine was unavailable, so only its Compose configuration was
validated.

## Test artifact

APK:
`C:\Users\thoma\AppData\Local\Temp\knock-knock-private-build\app\outputs\apk\debug\app-debug.apk`

Size: 271,143,633 bytes. SHA-256:

```text
2D9B76A050F442C3CC6E0248B51545148D071E229B2E479E5E4B97EBF0C286FB
```

The universal debug APK includes the bundled vision models and native libraries.
It remains in the isolated local build directory; it was not uploaded or published.
Use a tablet with a screen-lock credential. Do not uninstall an existing private
build merely to resolve a signature mismatch: uninstalling loses its private keys.

## Finish validation

Connect an authorized Android tablet with USB debugging, or provide enough disk
space for the emulator, then run from the project root:

```powershell
.\scripts\dev.ps1 -Mode Test -DeviceTests
```

The normal unified command is:

```powershell
.\scripts\dev.ps1 -Mode Test
```

See `private-android-testing.md` for setup and limitations. Before release, verify
the full import/unlock/review/correction/deletion/retention/export flow on hardware,
evaluate matching accuracy using consented test images, review model provenance,
and implement production signing and backup/recovery policy. Ring account-owner
verification and audio-free Ring ingestion need a separate, explicitly
network-enabled integration; no credentials or live Ring connection were added.

Existing unrelated working-tree changes were preserved. No Git commit, push,
cloud deployment, or public release was performed.
