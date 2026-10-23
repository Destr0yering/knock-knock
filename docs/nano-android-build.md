# Nano Android build environment

Nano is ARM64. This setup runs official Ubuntu amd64 tooling through the host's
QEMU/binfmt support, not an unofficial Android SDK distribution. It is slower
than a native x86 build. The NVMe mount is `/srv/nano`.

Prerequisites: Docker access, Java 17 and `qemu-user-static` on Nano. SDK license
acceptance was explicitly approved on 2026-10-12. Never automatically accept new
terms for an unrelated tool or service.

The source-only archive excludes `.gradle`, `.kotlin`, build directories, APKs,
archives, logs, `local.properties`, `.env` files, `google-services.json`, and signing
keystores. Only Android source, Gradle wrapper/configuration and bundled assets
are copied. Ring/AWS credentials and real visitor records are not transferred.

Dedicated paths:

- `/srv/nano/projects/knock-knock/source-build-20261012`: previous source copy.
- `/srv/nano/projects/knock-knock/knock-knock-android-src-20261014/knock-knock-android-src-20261014`: fresh, secret-free source copy used for the 2026-10-14 build.
- `/srv/nano/projects/knock-knock/gradle-cache`: dependency cache.
- `/srv/nano/projects/knock-knock/build-20261012`: previous generated output.
- `/srv/nano/projects/knock-knock/build-20261014`: current generated output.
- `/srv/nano/backups/knock-knock`: verified previous APK backup.

Container setup:

```bash
docker run --name knock-knock-sdk-20261012 --platform linux/amd64 --dns 1.1.1.1 \
  -e ACCEPT_ANDROID_SDK_LICENSES=yes \
  -v /srv/nano/projects/knock-knock/setup_nano_android.sh:/setup.sh:ro \
  ubuntu:22.04 bash /setup.sh
```

The container-scoped DNS setting avoids the observed default-container resolver
failure. It does not change host DNS or use privileged/host-network mode.
`scripts/setup_nano_android.sh` verifies Google's command-line-tools SHA-256,
installs platforms 35/36 and build tools 35/36, and checks package installation.
The old image lacked Android Platform-Tools, which Gradle tried to install as the
unprivileged build user into the root-owned SDK directory. Platform-Tools was
added to a new `knock-knock-android-builder:20261014` image; the original image
was preserved.

The current-source unit tests and debug build succeeded on 2026-10-14. The APK is
`/srv/nano/projects/knock-knock/build-20261014/app/outputs/apk/debug/app-debug.apk`
(270,951,480 bytes, SHA-256
`993da78251501836b1c42722148563f3f6bf83634e37e3d9a100c1e41dee907a`). It is a
debug build with no signing key and has not been installed on a device. Six
module test reports cover 14 tests (0 failures, 0 errors, 0 skipped). The app still removes INTERNET permission;
this build does not implement Ring linking, Cognito, or FCM.

After setup exits successfully, copy `scripts/build_android_nano.sh` and
`scripts/gradle-isolated.init.gradle` into the dedicated Nano project directory:

```bash
bash /srv/nano/projects/knock-knock/build_android_nano.sh
```

The build script runs unit tests and `:app:assembleDebug`, then prints the APK
checksum only if the build succeeds. Instrumented/device tests remain separate.

Do not install a newly generated Nano debug APK over an existing installation
without comparing signing certificates. This environment does not contain the
original Windows signing key. Never uninstall an app with private records just
to work around a signing mismatch. A successful build does not imply that the
unfinished Ring account-link and event-delivery integration is live.

## Firebase-enabled build - 2026-10-16

The Android client configuration was transferred separately to Nano at
`/srv/nano/projects/knock-knock/android-src-20261015-current-codex-v2/android/app/google-services.json`.
Gradle now reads the client entry matching `com.knockknock.app` and supplies its
Firebase project ID, Android app ID, sender ID, and client API key to the existing
Firebase initialization code. Cognito's public hosted domain and app-client ID
were supplied from the live `knock-knock-dev` CloudFormation outputs.

The build completed successfully without running the test suite. APK:
`/srv/nano/projects/knock-knock/build-20261016-firebase/app/outputs/apk/debug/app-debug.apk`
(272,635,618 bytes, SHA-256
`d8569a769653cd475fc02e1d109ca8d3c39742a855a1abcab089a474df6eb8c8`). The prior
Firebase-only APK is retained as `app-debug-firebase-only.apk`. The Firebase client
API key is present in the APK as expected for Android client configuration; do not
use a Firebase Admin credential or service-account private key in the app.

This is a debug build and has not been installed on the tablet. FCM still needs a
server-side Firebase credential in AWS Secrets Manager and a deployment of the
latest AWS source before a real event can deliver. No real Ring link or end-to-end
alert was validated by this build.

## Current source handoff - 2026-10-18

The current workspace Android source was copied to Nano as
`/srv/nano/projects/knock-knock/android-src-20261018-current.tar.gz` (SHA-256
`2b807152f7b14530ccff902f169f1c39216e82ade0d0af454acdbba67a5cea7b`). Nano
extracted it to `/srv/nano/projects/knock-knock/android-src-20261018-current`
and the previously approved Firebase Android client config is present there.
The initial wrapper invocation lacked the executable bit, so the build was
retried with `bash ./gradlew`. That attempt could not download Gradle 8.14.3
from `services.gradle.org` because Nano's outbound connection timed out. No
new APK was produced. Retry when Nano can reach the Gradle distribution host or
when its Gradle 8.14.3 distribution is populated in the wrapper cache. No tests
were run. The prior 2026-10-16 APK remains the last successful artifact and is
not a build of this current source snapshot.

## Current source build completed - 2026-10-19

Using the shared `/srv/nano/projects/knock-knock/gradle-cache` and the existing
`knock-knock-android-builder:20261014` image, Nano successfully ran
`:app:assembleDebug` against the 2026-10-18 source snapshot. The build was
compile-only; unit tests were not run. APK:
`/srv/nano/projects/knock-knock/android-src-20261018-current/app/build/outputs/apk/debug/app-debug.apk`
(272,493,057 bytes, SHA-256
`4e99fa1f5273c19197a27f0ecd52196f9fc99156ce54471e174d5def15ae3666`). A copy
is available in the project workspace at
`deliverables/knock-knock-debug-20261019.apk`; its SHA-256 matches Nano.
The build reported Android SDK XML version 4 compatibility, a redundant
RECORD_AUDIO removal, and deprecated FCM token/override declarations. These
were warnings; Gradle reported `BUILD SUCCESSFUL` (230 tasks).

Nano `adb devices -l` returned no attached devices. The APK has not been
installed; no device token, Ring event, or push notification has been tested.

## Current-source build attempt - 2026-10-22

The current workspace Android source was staged on Nano at
`/srv/nano/projects/knock-knock/android-src-20261022-current-v3/apps/android`.
The transfer excluded Gradle caches, generated outputs, local properties,
signing keys, and `google-services.json`; the previously approved Firebase
client config was copied from its existing Nano location into the staged source.
The snapshot contains current source and the Gradle wrapper/build configuration.

The debug build did not complete. Gradle could not resolve
`androidx.fragment:fragment:1.9.0` and other runtime dependencies because the
builder container could not resolve Google Maven or Maven Central. Nano itself
resolved their hostnames, but HTTPS requests to Google Maven timed out. The
build container produced no APK. No tests, deployment, or device installation
were run. Retry when Nano's outbound HTTPS access to Google Maven and Maven
Central is available, or after the required dependencies are cached.
