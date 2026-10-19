#!/usr/bin/env bash
# Clone every external code used by time_profiling at the commit the results were produced with.
#
#   bash time_profiling/environment/setup_external.sh            # into time_profiling/external (default)
#   TP_EXTERNAL=/somewhere/else bash time_profiling/environment/setup_external.sh
#
# Idempotent: an existing checkout is only moved to its pinned commit. Run setup_envs.sh afterwards: building
# the CosmoSIS standard library needs the cloe-cosmosis environment (it is done there).
# Locations must match time_profiling/tp_paths.py.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TP="$(dirname "$HERE")"
EXT="${TP_EXTERNAL:-$TP/external}"
DATA="${TP_DATA:-$TP/data}"
mkdir -p "$EXT"

clone() {   # clone <url> <dir> <commit> [<extra refspec to fetch>]
    local url="$1" dir="$EXT/$2" commit="$3" refspec="${4:-}"
    [ -d "$dir/.git" ] || git clone -q "$url" "$dir"
    [ -z "$refspec" ] || git -C "$dir" fetch -q origin "$refspec"
    git -C "$dir" -c advice.detachedHead=false checkout -q "$commit"
    echo "$2: $(git -C "$dir" log -1 --format='%h %ad %s' --date=short)"
}

CLOELIB=https://github.com/cloe-org/cloelib.git
CLOELIKE=https://github.com/cloe-org/cloelike.git
PR596='refs/pull/596/head:refs/remotes/origin/pr596'   # the non-linear-bias branch, merged and deleted

# Former CLOE (archived) and the CosmoSIS standard library
clone https://github.com/cloe-org/cloe.git cloe 1dd366050a42fe665db2dfd344fc0fc5d159fff5
clone https://github.com/joezuntz/cosmosis-standard-library.git cosmosis-standard-library \
      9e3dd611fc20bf39489d43bf4afeb503d26b4e79
# Fix for the id()-keyed interpolation cache in project_2d (validation_cosmosis_nonlinear_bias, section 5.1)
if git -C "$EXT/cosmosis-standard-library" apply --check "$HERE/patches/csl_interpolation_cache_fix.patch" 2>/dev/null; then
    git -C "$EXT/cosmosis-standard-library" apply "$HERE/patches/csl_interpolation_cache_fix.patch"
    echo "  applied csl_interpolation_cache_fix.patch"
fi

# cloelib versions (keys of tp_paths.CLOELIB)
clone "$CLOELIB" cloelib-pr596-c0f36e4 c0f36e4760f922a5bf556d32bc3f37d4b497c3cf "$PR596"   # Euclid DR3, z-convergence "384"
clone "$CLOELIB" cloelib-pr596-3f443c4 a24ccff396996bc0676485085331f88aa7492cb1 "$PR596"   # Euclid DR1, see below
# The DR1 runs used a local merge (3f443c4) of a24ccff with main (a59f0a4) whose conflict was resolved by hand;
# the patch reproduces its exact tree (db61aaea) on top of the published a24ccff.
if git -C "$EXT/cloelib-pr596-3f443c4" apply --check "$HERE/patches/cloelib_3f443c4_from_a24ccff.patch" 2>/dev/null; then
    git -C "$EXT/cloelib-pr596-3f443c4" apply "$HERE/patches/cloelib_3f443c4_from_a24ccff.patch"
fi
tree=$(cd "$EXT/cloelib-pr596-3f443c4" && git add -A && git write-tree && git reset -q)
[ "$tree" = db61aaea727b160d8bf9b5849a8e444a87bb3103 ] && echo "  patched to the DR1 tree db61aaea" \
    || { echo "cloelib-pr596-3f443c4: unexpected tree $tree" >&2; exit 1; }
clone "$CLOELIB" cloelib-2026-06-691c4f3 691c4f3a01bea1879e611cea92ddb421494c2b5d          # July 2026 speedcheck
clone "$CLOELIB" cloelib-main-0966dfa 0966dfa463d2c030e9767674d27e3e07970a8453             # 13-bin comparison, profiling
clone "$CLOELIB" cloelib-main-a59f0a4 a59f0a4f6d9ce9f1b35207c3c694d5d9de9a6fb9             # z-convergence "main"

# cloelike versions (keys of tp_paths.CLOELIKE)
clone "$CLOELIKE" cloelike-2026-04-b8c8bdc b8c8bdc79dd3e37821de0ddf7109f1c792f23ca7       # July 2026 speedcheck
clone "$CLOELIKE" cloelike-main-2d240ea 2d240ea4910c4ec30674c8f994ea8c5a5529158d

# The speedcheck's CLOE configs, copied into CLOE's configs/ (new files only); needs the data (fetch_data.py)
SC="$DATA/speedcheck_2026-07/their_files/cloefiles/configs"
if [ -d "$SC" ]; then
    cp -rn "$SC/." "$EXT/cloe/configs/" && echo "  copied the speedcheck CLOE configs into cloe/configs"
else
    echo "  (speedcheck data not found in $DATA: run data/fetch_data.py, then this script again)"
fi
