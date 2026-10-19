#!/usr/bin/env bash
# Create the conda environments of time_profiling, build the CosmoSIS standard library and register the
# Jupyter kernels. Run setup_external.sh first.
#
#   bash time_profiling/environment/setup_envs.sh                 # into time_profiling/environment/envs
#   TP_ENVS=/somewhere/else MAMBA=/path/to/mamba bash ...
#
#   cloe-cosmosis   cloelib, pyccl, CosmoSIS, Jupyter (kernel "cloe-cosmosis"): every notebook runs here
#   cloe-former     former CLOE (Python 3.9, cobaya 3.3.1): run as a subprocess by the notebooks
#   cloelib-zconv   ../numerical_validation/limber_z_convergence (kernel "cloelib-zconv")
#
# The YAML files leave a few packages unpinned (e.g. euclidlib); locks/ has the exact versions of the
# environments the results were produced with.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TP="$(dirname "$HERE")"
EXT="${TP_EXTERNAL:-$TP/external}"
ENVS="${TP_ENVS:-$HERE/envs}"
MAMBA="${MAMBA:-mamba}"
mkdir -p "$ENVS"

create() {   # create <name> <yaml>
    [ -d "$ENVS/$1" ] || "$MAMBA" env create -y -p "$ENVS/$1" -f "$HERE/$2"
}

# --- cloe-cosmosis ------------------------------------------------------------------------------------------
create cloe-cosmosis cloe-cosmosis-env-linux.yaml
PY="$ENVS/cloe-cosmosis/bin/python"
# cloelib's dependencies (+ camb, fast-pt extras). The notebooks put the cloelib version they need first on
# sys.path (tp_paths.CLOELIB) and assert it is the one imported, so this install only provides the dependencies.
"$PY" -m pip install -e "$EXT/cloelib-main-0966dfa[camb,fastpt]"
(   # the CosmoSIS standard library, compiled with the environment's compilers
    set +u
    export CONDA_PREFIX="$ENVS/cloe-cosmosis" PATH="$ENVS/cloe-cosmosis/bin:$PATH"
    for f in "$ENVS"/cloe-cosmosis/etc/conda/activate.d/*.sh; do source "$f"; done
    source cosmosis-configure
    cd "$EXT/cosmosis-standard-library"
    make -j 1     # -j 1: the legacy Fortran makefiles (isitgr, mgcamb) race on .mod files in parallel
)
"$PY" -m ipykernel install --user --name cloe-cosmosis --display-name "cloe-cosmosis (cloelib + pyccl + CosmoSIS)"

# --- cloe-former --------------------------------------------------------------------------------------------
create cloe-former cloe-former-env-linux.yaml
"$ENVS/cloe-former/bin/python" -m pip install -e "$EXT/cloe" --no-deps

# --- cloelib-zconv ------------------------------------------------------------------------------------------
create cloelib-zconv cloelib-zconv-env-linux.yaml
"$ENVS/cloelib-zconv/bin/python" -m pip install --no-cache-dir -e "$EXT/cloelib-main-a59f0a4[camb,fastpt]"
"$ENVS/cloelib-zconv/bin/python" -m ipykernel install --user --name cloelib-zconv --display-name "cloelib-zconv"

"$PY" - <<'EOF'
import cosmosis, pyccl, fastpt, camb, jax
print("cloe-cosmosis: cosmosis", cosmosis.__version__, "| pyccl", pyccl.__version__, "| fast-pt", fastpt.__version__,
      "| camb", camb.__version__, "| jax", jax.__version__)
EOF
