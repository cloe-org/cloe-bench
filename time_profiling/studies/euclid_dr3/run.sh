#!/usr/bin/env bash
# Execute the notebooks of the Euclid DR3-like (13 SPV3 bins) study, each pinned with taskset.
#
#   bash run.sh                      # both comparisons
#   bash run.sh four_codes           # time_comparison_Euclid_DR3.ipynb: 1 core, then the full budget (section 5.2)
#   bash run.sh cloe_vs_cloelib      # time_comparison_cloe_vs_cloelib_13bins.ipynb: 8 CPUs, in place
#   CPUS_1=5 CPUS_FULL=0-127 CPUS_8=56-63 bash run.sh
#
# OMP/MKL/OPENBLAS_NUM_THREADS are set to the number of CPUs (JAX/XLA sizes its thread pool from the
# affinity mask). time_comparison_Euclid_DR3.ipynb labels its results and figures from the number of CPUs
# it sees: "_1core" on one core, no suffix otherwise. The October 2026 four-code runs used `taskset -c 5`
# and an unrecorded 128-core host; the defaults below are healthy cores of drontermeer (2026-10, socket 0
# throttled). Python: the cloe-cosmosis environment (TP_ENVS, see time_profiling/tp_paths.py).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TP="$(cd "$ROOT/../.." && pwd)"
PY="${TP_ENVS:-$TP/environment/envs}/cloe-cosmosis/bin/python"
CPUS_1="${CPUS_1:-48}"                    # one physical core on NUMA node 1
CPUS_8="${CPUS_8:-48-55}"                 # 8 physical cores on NUMA node 1
CPUS_FULL="${CPUS_FULL:-48-95,144-191}"   # NUMA node 1 of drontermeer (socket 0 throttled to 400 MHz)

run() {   # run <cpu list> <notebook> <output notebook>
    local cpus="$1" nb="$2" out="$3" n
    n=$(taskset -c "$cpus" "$PY" -c 'import os; print(len(os.sched_getaffinity(0)))')
    echo "=== $(date '+%F %T')  taskset -c $cpus ($n CPUs) $(basename "$nb") -> $(basename "$out")"
    OMP_NUM_THREADS=$n MKL_NUM_THREADS=$n OPENBLAS_NUM_THREADS=$n \
        taskset -c "$cpus" "$PY" -m jupyter nbconvert --to notebook --execute "$nb" --output "$out" \
        --ExecutePreprocessor.kernel_name=cloe-cosmosis --ExecutePreprocessor.timeout=-1
}

cd "$ROOT"
case "${1:-all}" in
    four_codes|all)
        run "$CPUS_1" time_comparison_Euclid_DR3.ipynb "$ROOT/time_comparison_Euclid_DR3_1core.ipynb"
        run "$CPUS_FULL" time_comparison_Euclid_DR3.ipynb "$ROOT/time_comparison_Euclid_DR3.ipynb" ;;&
    cloe_vs_cloelib|all)
        run "$CPUS_8" time_comparison_cloe_vs_cloelib_13bins.ipynb "$ROOT/time_comparison_cloe_vs_cloelib_13bins.ipynb" ;;
    four_codes) ;;
    *) echo "usage: bash run.sh [four_codes|cloe_vs_cloelib|all]" >&2; exit 2 ;;
esac
