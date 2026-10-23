#!/usr/bin/env bash
set -euo pipefail
# Run only inside the official amd64 Ubuntu container, with approved licenses.
test "${ACCEPT_ANDROID_SDK_LICENSES:-no}" = yes
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends openjdk-17-jdk-headless ca-certificates curl unzip git
export ANDROID_HOME=/opt/android-sdk
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
curl --fail --location --retry 3 \
  https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip \
  -o /tmp/android-tools.zip
echo '4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583  /tmp/android-tools.zip' | sha256sum -c -
mkdir -p "$ANDROID_HOME/cmdline-tools"
unzip -q /tmp/android-tools.zip -d "$ANDROID_HOME/cmdline-tools"
mv "$ANDROID_HOME/cmdline-tools/cmdline-tools" "$ANDROID_HOME/cmdline-tools/latest"
# yes may exit SIGPIPE after sdkmanager closes stdin; check sdkmanager itself.
set +o pipefail
yes | sdkmanager --licenses >/dev/null
license_status=${PIPESTATUS[1]}
set -o pipefail
test "$license_status" = 0
sdkmanager 'platforms;android-35' 'platforms;android-36' 'build-tools;35.0.0' 'build-tools;36.0.0'
java -version
sdkmanager --list_installed
