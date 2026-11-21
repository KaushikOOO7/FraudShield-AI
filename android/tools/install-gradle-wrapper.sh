#!/bin/sh
set -eu
APP_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
WRAPPER_DIR="$APP_ROOT/gradle/wrapper"
WRAPPER_SHA=$(curl --fail --silent --show-error --location --connect-timeout 15 'https://services.gradle.org/distributions/gradle-8.7-wrapper.jar.sha256')
DIST_SHA=$(curl --fail --silent --show-error --location --connect-timeout 15 'https://services.gradle.org/distributions/gradle-8.7-bin.zip.sha256')
case "$WRAPPER_SHA$DIST_SHA" in *[!a-fA-F0-9]*) echo 'Invalid Gradle checksum response' >&2; exit 1;; esac
[ "${#WRAPPER_SHA}" -eq 64 ] && [ "${#DIST_SHA}" -eq 64 ]
curl --fail --silent --show-error --location --connect-timeout 15 --output "$WRAPPER_DIR/gradle-wrapper.jar.download" 'https://raw.githubusercontent.com/gradle/gradle/v8.7.0/gradle/wrapper/gradle-wrapper.jar'
if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL_SHA=$(sha256sum "$WRAPPER_DIR/gradle-wrapper.jar.download" | cut -d ' ' -f 1)
else
    ACTUAL_SHA=$(shasum -a 256 "$WRAPPER_DIR/gradle-wrapper.jar.download" | cut -d ' ' -f 1)
fi
[ "$ACTUAL_SHA" = "$WRAPPER_SHA" ] || { echo 'Gradle wrapper SHA-256 verification failed' >&2; exit 1; }
sed '/^distributionSha256Sum=/d' "$WRAPPER_DIR/gradle-wrapper.properties" > "$WRAPPER_DIR/gradle-wrapper.properties.download"
printf '\ndistributionSha256Sum=%s\n' "$DIST_SHA" >> "$WRAPPER_DIR/gradle-wrapper.properties.download"
mv "$WRAPPER_DIR/gradle-wrapper.properties.download" "$WRAPPER_DIR/gradle-wrapper.properties"
mv "$WRAPPER_DIR/gradle-wrapper.jar.download" "$WRAPPER_DIR/gradle-wrapper.jar"
echo 'Official Gradle 8.7 wrapper installed and verified. Commit the JAR and pinned distribution checksum.'
