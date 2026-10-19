#!/usr/bin/env bash
# Execute speedcheck_reanalysis.ipynb pinned to 8 CPUs of NUMA node 1 (see the notebook's introduction).
#   bash run.sh            # CPUS=48-55 by default
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPUS="${CPUS:-48-55}"
PY="${TP_ENVS:-$HERE/../../environment/envs}/cloe-cosmosis/bin/python"
N=$(taskset -c "$CPUS" "$PY" -c 'import os; print(len(os.sched_getaffinity(0)))')
cd "$HERE"
OMP_NUM_THREADS=$N MKL_NUM_THREADS=$N OPENBLAS_NUM_THREADS=$N taskset -c "$CPUS" \
    "$PY" -m jupyter nbconvert --to notebook --execute --inplace \
    speedcheck_reanalysis.ipynb --ExecutePreprocessor.kernel_name=cloe-cosmosis --ExecutePreprocessor.timeout=-1
