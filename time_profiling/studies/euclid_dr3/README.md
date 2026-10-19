# Euclid DR3-like (13 SPV3 bins): cloelib vs former CLOE, pyccl and CosmoSIS

Two comparisons on the same 13 SPV3 bins (`nzTabSPV3.fits`, 351 spectra).

## 1. Four codes, $n_\ell$ and $N_Z$ sweeps

**Set-up.** TATT + one-loop galaxy bias, $n_\ell$ = 32–3000, $N_Z$ = 100–250. Run on 1 core and with default threading on 128 cores.

**Headline.** On 1 core cloelib is the fastest code at every $n_\ell$: 3.5–16x faster than pyccl, 2.6–3.3x faster than CosmoSIS and 2.7–5x faster than former CLOE. With 128 free cores, pyccl ties with cloelib from $n_\ell \approx 500$.

## 2. Former CLOE vs cloelib at the analysis set-up

**Set-up.** 32 ℓ values, $N_Z$ = 100–1000. Two models: linear bias + NLA (the July 2026 speedcheck's model) and one-loop bias + TATT. Run on 8 CPUs of NUMA node 1 of `drontermeer`.

**Headline.** At $N_Z = 600$ cloelib is 1.6x faster with linear bias + NLA (0.19 vs 0.29 s) and 4.7x faster with one-loop bias + TATT (0.48 vs 2.25 s).

## Files

| file | what |
|---|---|
| `time_comparison_Euclid_DR3.ipynb` | comparison 1, executed with default threading (128 cores) |
| `time_comparison_Euclid_DR3_1core.ipynb` | the same notebook, executed on 1 core |
| `time_comparison_cloe_vs_cloelib_13bins.ipynb` | comparison 2; it runs `../../benchmarks/cloelib_benchmark.py` and `../../benchmarks/cloe_former_benchmark.py` as subprocesses |
| `run.sh` | executes the notebooks: `bash run.sh [four_codes\|cloe_vs_cloelib\|all]` (CPU sets: `CPUS_1`, `CPUS_FULL`, `CPUS_8`) |
| `results/` | outputs. Comparison 1: `cloe_former_*` (names ending in `_1core` from the 1-core run). Comparison 2: `cloelib_{linear,pt}.*`, `cloe_{linear,pt}_nz*.*` |

Figures are not tracked in git: the executed notebooks show them, and running the notebooks writes them to `figures/`.

Versions: see the provenance table in [`../README.md`](../README.md). The host of the comparison-1 runs was not recorded.
