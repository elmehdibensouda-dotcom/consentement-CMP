#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: scripts/prepare-web-pilot-handoff.sh <transfer-label> <output-dir>

Create a Web-only customer test package from the current clean Git commit.
The package is a staging evaluation handoff, not a production release.
EOF
  exit 2
}

[[ $# -eq 2 ]] || usage
transfer_label="$1"
output_dir="$2"

if [[ ! "$transfer_label" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]]; then
  echo "Transfer label must be 1-64 letters, digits, dots, underscores, or hyphens." >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Run this command from a Git checkout of ALAMANE." >&2
  exit 2
}
if [[ -n "$(git -C "$repo_root" status --porcelain --untracked-files=all)" ]]; then
  echo "The source checkout must be clean before preparing a client handoff." >&2
  exit 2
fi

source_commit="$(git -C "$repo_root" rev-parse HEAD)"
if [[ ! "$source_commit" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Could not resolve a full source commit." >&2
  exit 2
fi

required_paths=(
  Dockerfile backend schemas ops/container/entrypoint.sh
  ops/container/README.md ops/container/staging.env.example
  ops/container/staging-migrate.env.example ops/postgres-runtime-privileges.sql
  admin.html index.html aman-cmp.js aman-scanner.js demo-site.html
  demo-assurance.html scanner-tool.html demo-tags SDK_WEB.md
  GUIDE_INTEGRATION_PILOTE.md PILOTE_WEB_FERME.md PILOTE_CLIENT_WEB.md
  DOSSIER_SECURITE_FOURNISSEUR.md
)
for path in "${required_paths[@]}"; do
  if ! git -C "$repo_root" cat-file -e "HEAD:$path" 2>/dev/null; then
    echo "Required committed handoff path is missing: $path" >&2
    exit 2
  fi
done

if command -v sha256sum >/dev/null 2>&1; then
  digest_tool=sha256sum
elif command -v shasum >/dev/null 2>&1; then
  digest_tool=shasum
else
  echo "Install sha256sum or shasum to create the transfer manifest." >&2
  exit 2
fi

mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
archive="$output_dir/alamane-web-pilot-${transfer_label}-${source_commit}.tar.gz"
checksum="${archive}.sha256"
if [[ -e "$archive" || -e "$checksum" ]]; then
  echo "Refusing to overwrite an existing handoff archive or checksum: $archive" >&2
  exit 2
fi

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/alamane-web-pilot.XXXXXX")"
bundle="$temp_dir/alamane-web-pilot-${transfer_label}-${source_commit}"
temporary_archive="$output_dir/.$(basename "$archive").tmp.$$"
temporary_checksum="$output_dir/.$(basename "$checksum").tmp.$$"
publish_complete=0
cleanup() {
  rm -rf "$temp_dir"
  rm -f "$temporary_archive" "$temporary_checksum"
  if [[ "$publish_complete" != "1" ]]; then
    rm -f "$archive" "$checksum"
  fi
}
trap cleanup EXIT

mkdir -p "$bundle/source"
git -C "$repo_root" archive --format=tar --prefix=source/ HEAD "${required_paths[@]}" \
  | tar -xf - -C "$bundle"
cp "$repo_root/PILOTE_CLIENT_WEB.md" "$bundle/README-PILOTE.md"

cat > "$bundle/BUILD-INFO.txt" <<EOF
transfer_label=$transfer_label
source_commit=$source_commit
source_branch=$(git -C "$repo_root" branch --show-current)
created_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
scope=web-only-staging-evaluation
EOF

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
if [[ "$digest_tool" == "sha256sum" ]]; then
  archive_digest="$(sha256sum "$temporary_archive")"
else
  archive_digest="$(shasum -a 256 "$temporary_archive")"
fi
printf '%s  %s\n' "${archive_digest%% *}" "$(basename "$archive")" > "$temporary_checksum"
mv "$temporary_checksum" "$checksum"
mv "$temporary_archive" "$archive"
publish_complete=1

echo "Created Web pilot handoff: $archive"
echo "Archive SHA-256: $checksum"
echo "Source commit: $source_commit"
