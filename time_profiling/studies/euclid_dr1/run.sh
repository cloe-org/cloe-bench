#!/usr/bin/env bash
# Execute time_comparison_Euclid_DR1.ipynb once per CPU budget: 8 CPUs, then the full budget (see the notebook's introduction).
#
#   bash run.sh                       # 8 CPUs, then 96 CPUs (defaults below)
#   CPUS_8=56-63 CPUS_FULL=0-127 bash run.sh
#
# Each run is pinned with taskset, and OMP/MKL/OPENBLAS_NUM_THREADS are set to the number of CPUs
# (JAX/XLA sizes its thread pool from the affinity mask). The 8-CPU run goes first: the full-budget run,
# executed in place, then reads both results/timings_Euclid_DR1_<N>cpu.json files in its section 4.1.
# The default CPU sets are those of drontermeer (2026-10, socket 0 throttled); pick sets of healthy cores
# on your machine. Python: the cloe-cosmosis environment (TP_ENVS, see time_profiling/tp_paths.py).
#
# Check the node before trusting the numbers: the notebook prints the clock of the CPUs it runs on
# and warns if any is below 1 GHz (e.g. a throttled socket), and it records the load average.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TP="$(cd "$ROOT/../.." && pwd)"
PY="${TP_ENVS:-$TP/environment/envs}/cloe-cosmosis/bin/python"
NB="$ROOT/time_comparison_Euclid_DR1.ipynb"
CPUS_8="${CPUS_8:-48-55}"       # 8 physical cores on one NUMA node
CPUS_FULL="${CPUS_FULL:-48-95,144-191}"   # NUMA node 1 of drontermeer (socket 0 throttled to 400 MHz)

run() {   # run <cpu list> <output notebook>
    local cpus="$1" out="$2" n
    n=$(taskset -c "$cpus" "$PY" -c 'import os; print(len(os.sched_getaffinity(0)))')
    echo "=== $(date '+%F %T')  taskset -c $cpus ($n CPUs) -> $(basename "$out")"
    OMP_NUM_THREADS=$n MKL_NUM_THREADS=$n OPENBLAS_NUM_THREADS=$n \
        taskset -c "$cpus" "$PY" -m jupyter nbconvert --to notebook --execute "$NB" --output "$out" \
        --ExecutePreprocessor.kernel_name=cloe-cosmosis --ExecutePreprocessor.timeout=-1
}

cd "$ROOT"
run "$CPUS_8" "$ROOT/time_comparison_Euclid_DR1_8cpu.ipynb"
run "$CPUS_FULL" "$NB"
