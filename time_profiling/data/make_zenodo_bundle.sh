#!/usr/bin/env bash
# Build the archive to upload to Zenodo from this folder, and refresh MANIFEST.sha256 (commit it).
#
#   bash make_zenodo_bundle.sh [version]        # -> time_profiling_data_<version>.tar.gz (default v1)
#
# Packs every payload file (everything here except this script, fetch_data.py, README.md, MANIFEST.sha256,
# .gitignore and previous archives). Upload the archive as the single file of the Zenodo record, then put the
# record's DOI and file URL in fetch_data.py (ZENODO_URL) and in README.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
VERSION="${1:-v1}"
OUT="time_profiling_data_${VERSION}.tar.gz"
PAYLOAD="$(mktemp)"
trap 'rm -f "$PAYLOAD"' EXIT
find . -type f ! -name '*.tar.gz' ! -name make_zenodo_bundle.sh ! -name fetch_data.py ! -name README.md \
     ! -name MANIFEST.sha256 ! -name .gitignore ! -path '*/__pycache__/*' -printf '%P\n' | LC_ALL=C sort > "$PAYLOAD"
xargs -d '\n' sha256sum < "$PAYLOAD" > MANIFEST.sha256
tar -czf "$OUT" -T "$PAYLOAD" MANIFEST.sha256
echo "$OUT: $(du -h "$OUT" | cut -f1), $(wc -l < MANIFEST.sha256) files; sha256 $(sha256sum "$OUT" | cut -d' ' -f1)"
