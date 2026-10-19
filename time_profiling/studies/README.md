# Studies

One folder per question. Each one has a `README.md`, a `run.sh`, its notebook(s) and `results/` (JSON, npz, logs). Figures are not tracked in git: the executed notebooks show them, and running a notebook writes them to its study's `figures/`.

Each study times **one full photometric 3x2pt evaluation from scratch, CAMB excluded**: every step after the Boltzmann solver, with nothing cached between evaluations. That covers each code's own background, growth and P(k) interpolators, the tracers and kernels, all FAST-PT loops, and the Limber projection of every spectrum. All codes receive the same n(z) arrays and the same number of redshift points. The **first call** at each array shape is reported separately, because for cloelib it includes JAX compilation.

| study | question | set-up | headline |
|---|---|---|---|
| [`cloelib_profiling/`](cloelib_profiling) | where cloelib's time goes, and how it scales | 13 and 6 bins, linear + NLA and one-loop + TATT, $N_Z$ and $n_\ell$ sweeps, 1 / 8 / 96 CPUs | at the analysis set-up 0.13 s (linear + NLA) / 0.39 s (one-loop + TATT), half or more in one-at-a-time JAX operations |
| [`euclid_dr3/`](euclid_dr3) | four codes, Euclid DR3-like | 13 bins, 351 spectra, TATT + one-loop bias, $n_\ell$ 32–3000, $N_Z$ 100–250; 128 cores and 1 core | cloelib fastest on 1 core at every $n_\ell$ (3.5–16x pyccl, 2.6–3.3x CosmoSIS, 2.7–5x former CLOE); with 128 free cores pyccl ties from $n_\ell\approx500$ |
| ↳ same folder | former CLOE vs cloelib at the analysis set-up | 13 bins, 32 $\ell$, $N_Z$ 100–1000, linear+NLA and one-loop+TATT, 8 CPUs | at $N_Z = 600$: cloelib 1.6x faster (linear + NLA) and 4.7x faster (one-loop + TATT) |
| [`euclid_dr1/`](euclid_dr1) | the same, Euclid DR1-like, laptop vs node | 6 bins, 78 spectra, 8 vs 96 CPUs | on 8 CPUs cloelib fastest at every $n_\ell$; only pyccl uses extra CPUs and overtakes from $n_\ell\approx500$ |
| [`speedcheck_reanalysis/`](speedcheck_reanalysis) | why the July 2026 speedcheck found CLOE 2.5x (40x without JIT) faster | its exact set-up: 10 bins, 20 $\ell$, 100 $z$, linear + NLA | reproduced (2.1x). The cause is cloelib's eager-JAX overhead on a tiny problem, plus a June-2026 cloelike that ran CAMB 3x per call; `JAX_DISABLE_JIT=1` is a debugging mode |
| [`_archive/early_exploration/`](_archive/early_exploration) | first exploration (September 2026) | | record only; not runnable in this layout |

## Shared pieces

- The timing tools are in [`../benchmarks/`](../benchmarks): `cloelib_benchmark.py`, `cloe_former_benchmark.py` (run in the cloe-former env as a subprocess) and the CosmoSIS pipeline `cosmosis/pipeline_3x2pt_tatt_nlbias.ini` (its values and n(z) files are generated into `TP_WORK`).
- The inputs are in [`../data/`](../data), on Zenodo (`fetch_data.py`).
- All paths come from [`../tp_paths.py`](../tp_paths.py).

## Running a study

Set-up (external codes, environments, data): see [`../README.md`](../README.md). Then, for example:

```bash
cd time_profiling/studies/euclid_dr1
CPUS_8=48-55 CPUS_FULL=48-95,144-191 bash run.sh
```

Each `run.sh` executes its notebook with `jupyter nbconvert --execute` under `taskset`, with `OMP/MKL/OPENBLAS_NUM_THREADS` set to the number of CPUs. The thread pools of JAX, OpenMP and BLAS are sized when the process starts, so one kernel equals one CPU budget. Before trusting a timing, check the node:
- the notebooks print the clock of the CPUs they run on, and warn below 1 GHz;
- they wait for a quiet node (`LOAD_MAX`) and log the load average at every point.

## Provenance

The executed notebooks in these folders are the October 2026 runs. Each one starts with a note giving the host, date and CPU set. They were moved here from a working directory afterwards: only their path handling changed, and local paths in their outputs read `<WORKDIR>`.

| study | cloelib | other codes |
|---|---|---|
| `cloelib_profiling` | `main` at `0966dfa` | |
| `euclid_dr3` | PR #596 at `c0f36e4` | CLOE `1dd3660`, CSL `9e3dd611` + patch, pyccl 3.3.6, CAMB 1.6.5 |
| `euclid_dr1` | PR #596 at `3f443c4` = `a24ccff` + `environment/patches/cloelib_3f443c4_from_a24ccff.patch` | as above |
| `euclid_dr3`, CLOE vs cloelib | `main` at `0966dfa` | CLOE `1dd3660` |
| `speedcheck_reanalysis` | `691c4f3` (June 2026) and `0966dfa`; cloelike `b8c8bdc` and `2d240ea` | CLOE `1dd3660` |

**The `euclid_dr3` host was not recorded.** It had 128 cores, and its CPU model is not known. The other studies ran on `drontermeer` (2 × AMD EPYC 9454) restricted to NUMA node 1, because socket 0 was throttled to 400 MHz at the time. Compare ratios between codes within one study, not absolute times across studies.
