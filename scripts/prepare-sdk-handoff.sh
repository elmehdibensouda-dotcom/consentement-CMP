#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: prepare-sdk-handoff.sh <transfer-label> <web-preview-dir> <mobile-preview-dir> <ios-preview-dir> <output-dir>

The three preview directories must come from manual Product validation runs for
the same 40-character source commit. The script verifies their SHA-256 manifests
and produces one transfer archive; it does not build, sign, publish, or attest
the SDKs.
EOF
  exit 2
}

[[ $# -eq 5 ]] || usage
transfer_label="$1"
web_preview="$2"
mobile_preview="$3"
ios_preview="$4"
output_dir="$5"

if [[ ! "$transfer_label" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]]; then
  echo "Transfer label must be 1-64 letters, digits, dots, underscores, or hyphens." >&2
  exit 2
fi

for preview in "$web_preview" "$mobile_preview" "$ios_preview"; do
  if [[ ! -d "$preview" || ! -f "$preview/BUILD-INFO.txt" || ! -f "$preview/SHA256SUMS" ]]; then
    echo "Each preview must contain BUILD-INFO.txt and SHA256SUMS: $preview" >&2
    exit 2
  fi
done

verify_manifest() {
  local preview="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$preview" && sha256sum --check --strict SHA256SUMS)
  elif command -v shasum >/dev/null 2>&1; then
    (cd "$preview" && shasum -a 256 -c SHA256SUMS)
  else
    echo "Install sha256sum or shasum to verify preview manifests." >&2
    exit 2
  fi
}

for preview in "$web_preview" "$mobile_preview" "$ios_preview"; do
  verify_manifest "$preview"
done

read_source_commit() {
  local preview="$1"
  sed -n 's/^source_commit=//p' "$preview/BUILD-INFO.txt" | head -n 1
}

web_commit="$(read_source_commit "$web_preview")"
mobile_commit="$(read_source_commit "$mobile_preview")"
ios_commit="$(read_source_commit "$ios_preview")"
if [[ ! "$web_commit" =~ ^[0-9a-f]{40}$ || "$web_commit" != "$mobile_commit" || "$web_commit" != "$ios_commit" ]]; then
  echo "Preview source commits must match and contain the same full 40-character SHA." >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Run this command from a clean checkout of the source repository." >&2
  exit 2
}
repo_commit="$(git -C "$repo_root" rev-parse HEAD)"
if [[ "$repo_commit" != "$web_commit" ]]; then
  echo "The checkout ($repo_commit) does not match the artifact source commit ($web_commit)." >&2
  exit 2
fi
if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  echo "The source checkout must be clean before preparing a client handoff." >&2
  exit 2
fi

for preview in "$web_preview" "$mobile_preview" "$ios_preview"; do
  if [[ -z "$(sed -n 's/^workflow_run=//p' "$preview/BUILD-INFO.txt" | head -n 1)" ]]; then
    echo "A preview is missing its workflow run URL: $preview" >&2
    exit 2
  fi
done

for expected in \
  "$web_preview/aman-cmp.js" \
  "$web_preview/WEB-INTEGRATION.md" \
  "$mobile_preview/sample-debug.apk" \
  "$mobile_preview/maven-repository/ma/aman/aman-consent-android/0.1.0/aman-consent-android-0.1.0.aar" \
  "$mobile_preview/maven-repository/ma/aman/aman-consent-android/0.1.0/aman-consent-android-0.1.0.pom" \
  "$mobile_preview/maven-repository/ma/aman/aman-consent-android/0.1.0/aman-consent-android-0.1.0-sources.jar" \
  "$mobile_preview/react-native/aman-consent-react-native-0.1.0.tgz" \
  "$mobile_preview/react-native/alamane-react-native.sbom.cdx.json" \
  "$ios_preview/aman-consent-ios-source.tar.gz"; do
  if [[ ! -f "$expected" ]]; then
    echo "Required SDK handoff file is missing: $expected" >&2
    exit 2
  fi
done

mkdir -p "$output_dir"
archive="$output_dir/alamane-sdk-pilot-${transfer_label}-${web_commit}.tar.gz"
archive_checksum="${archive}.sha256"
if [[ -e "$archive" || -e "$archive_checksum" ]]; then
  echo "Refusing to overwrite an existing handoff archive or checksum: $archive" >&2
  exit 2
fi

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/alamane-sdk-handoff.XXXXXX")"
temporary_archive="$output_dir/.$(basename "$archive").tmp.$$"
temporary_checksum="$output_dir/.$(basename "$archive_checksum").tmp.$$"
publish_complete=0
cleanup() {
  rm -rf "$temp_dir"
  rm -f "$temporary_archive" "$temporary_checksum"
  if [[ "$publish_complete" != "1" ]]; then
    rm -f "$archive" "$archive_checksum"
  fi
}
trap cleanup EXIT
bundle="$temp_dir/alamane-sdk-pilot-${transfer_label}-${web_commit}"
mkdir -p "$bundle/web" "$bundle/android" "$bundle/react-native" "$bundle/ios" "$bundle/documentation"

cp "$web_preview/aman-cmp.js" "$web_preview/WEB-INTEGRATION.md" "$bundle/web/"
cp -R "$mobile_preview/maven-repository" "$bundle/android/"
cp "$mobile_preview/sample-debug.apk" "$bundle/android/"
cp "$mobile_preview/react-native/aman-consent-react-native-0.1.0.tgz" \
  "$mobile_preview/react-native/alamane-react-native.sbom.cdx.json" \
  "$bundle/react-native/"
cp "$ios_preview/aman-consent-ios-source.tar.gz" "$bundle/ios/"
cp "$repo_root/GUIDE_INTEGRATION_PILOTE.md" \
  "$repo_root/mobile/android/README.md" \
  "$repo_root/mobile/ios/README.md" \
  "$repo_root/mobile/react-native/README.md" \
  "$bundle/documentation/"

cat > "$bundle/HANDOFF.md" <<EOF
# ALAMANE SDK pilot handoff

- Transfer label (not an SDK release version): $transfer_label
- Source commit: $web_commit
- Web preview run: $(sed -n 's/^workflow_run=//p' "$web_preview/BUILD-INFO.txt" | head -n 1)
- Mobile preview run: $(sed -n 's/^workflow_run=//p' "$mobile_preview/BUILD-INFO.txt" | head -n 1)
- iOS preview run: $(sed -n 's/^workflow_run=//p' "$ios_preview/BUILD-INFO.txt" | head -n 1)

This is a source and evaluation handoff, not a production release. The Android
sample APK is debug-signed. The Android Maven repository includes the AAR, POM,
Gradle module metadata, and sources JAR, but the artifacts are not signed as
ALAMANE releases. The React Native CycloneDX SBOM covers only that package's
npm dependency graph; Android and iOS SBOMs are not included. SHA256SUMS detects
changes after packaging; it does not prove build provenance or replace a
cryptographic signature or attestation. Review the contents and transfer them
only through the customer's approved artifact repository and process.
EOF

if command -v sha256sum >/dev/null 2>&1; then
  digest_tool=sha256sum
else
  digest_tool=shasum
fi
(
  cd "$bundle"
  find . -type f ! -name SHA256SUMS -print | LC_ALL=C sort | while IFS= read -r file; do
    if [[ "$digest_tool" == "sha256sum" ]]; then
      sha256sum "$file"
    else
      shasum -a 256 "$file"
    fi
  done > SHA256SUMS
)

tar -czf "$temporary_archive" -C "$temp_dir" "$(basename "$bundle")"
if command -v sha256sum >/dev/null 2>&1; then
  archive_digest="$(sha256sum "$temporary_archive")"
else
  archive_digest="$(shasum -a 256 "$temporary_archive")"
fi
printf '%s  %s\n' "${archive_digest%% *}" "$(basename "$archive")" > "$temporary_checksum"
mv "$temporary_checksum" "$archive_checksum"
mv "$temporary_archive" "$archive"
publish_complete=1
echo "Created SDK pilot handoff: $archive"
echo "Archive SHA-256: $archive_checksum"
echo "Source commit: $web_commit"
