#!/usr/bin/env bash
set -euo pipefail
# Execute on Nano after the SDK setup container has exited successfully.
project_root=/srv/nano/projects/knock-knock
android_src=${KNOCK_KNOCK_ANDROID_SOURCE:-$project_root/knock-knock-android-src-20261014/knock-knock-android-src-20261014}
build_output=${KNOCK_KNOCK_ANDROID_OUTPUT:-$project_root/build-20261014}
builder_image=${KNOCK_KNOCK_ANDROID_IMAGE:-knock-knock-android-builder:20261014}
test -x "$android_src/gradlew"
mkdir -p "$project_root/gradle-cache/home" "$build_output"
docker run --rm --platform linux/amd64 --dns 1.1.1.1 \
  --user "$(id -u):$(id -g)" \
  -e HOME=/gradle-cache/home \
  -e GRADLE_USER_HOME=/gradle-cache \
  -e ANDROID_HOME=/opt/android-sdk \
  -e ANDROID_SDK_ROOT=/opt/android-sdk \
  -e JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
  -e JAVA_TOOL_OPTIONS=-Duser.home=/gradle-cache/home \
  -e KNOCK_KNOCK_BUILD_ROOT=/build-output \
  -e ORG_GRADLE_PROJECT_cognitoDomainUrl="${KNOCK_KNOCK_COGNITO_DOMAIN_URL:-}" \
  -e ORG_GRADLE_PROJECT_cognitoClientId="${KNOCK_KNOCK_COGNITO_CLIENT_ID:-}" \
  -v "$android_src:/workspace" \
  -v "$project_root/gradle-cache:/gradle-cache" \
  -v "$build_output:/build-output" \
  -v "$project_root/gradle-isolated.init.gradle:/isolate.gradle:ro" \
  -w /workspace "$builder_image" \
  bash gradlew --no-daemon --max-workers=2 --console=plain \
  --init-script /isolate.gradle testDebugUnitTest :app:assembleDebug
apk="$build_output/app/outputs/apk/debug/app-debug.apk"
test -s "$apk"
sha256sum "$apk"
