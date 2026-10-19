#!/usr/bin/env bash
# Execute cloelib_profiling.ipynb in place, pinned to a CPU set. The notebook runs its measurements on the
# first 1, 8 and all CPUs of that set, so give it a set of healthy, idle cores on one machine.
#   bash run.sh                  # CPUS=48-95,144-191 (NUMA node 1 of drontermeer)
#   CPUS=0-63 bash run.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPUS="${CPUS:-48-95,144-191}"
PY="${TP_ENVS:-$HERE/../../environment/envs}/cloe-cosmosis/bin/python"
cd "$HERE"
taskset -c "$CPUS" "$PY" -m jupyter nbconvert --to notebook --execute --inplace cloelib_profiling.ipynb \
    --ExecutePreprocessor.kernel_name=cloe-cosmosis --ExecutePreprocessor.timeout=-1
