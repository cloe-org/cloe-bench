# time_profiling

How fast is cloelib, where does its time go, and how does it compare with former CLOE, pyccl and CosmoSIS on the same task?

- **[`studies/`](studies)**: one folder per question. `cloelib_profiling/` looks at cloelib on its own (cost per stage, scaling, JAX compilation, CPU budgets); the other three compare it with the other codes on identical inputs and grids. See the [studies README](studies/README.md).
- The accuracy side of the same redshift grids is a separate module of cloe-bench: [`../numerical_validation/limber_z_convergence/`](../numerical_validation/limber_z_convergence). It uses this folder's `tp_paths.py`, environments and data.
- **[`benchmarks/`](benchmarks)**: the timing tools the studies share (cloelib, former CLOE, the CosmoSIS pipeline).

**Interactive results:** a dashboard with the charts of every study, each number linked to its source file in this repository: <https://claude.ai/artifact/AFS2bEJHWXWLBB86zg6W3X>. It is built from `dashboard/` (`build_dashboard_data.py` turns the committed results into its datasets).

## Findings in brief

Times are one full photometric 3x2pt evaluation, CAMB excluded.

| question | answer | where |
|---|---|---|
| CLOE vs cloelib at the analysis set-up (13 bins, 32 ℓ, $N_Z = 600$, 8 CPUs) | cloelib **1.6x** faster with linear bias + NLA (0.19 vs 0.29 s), **4.7x** faster with one-loop bias + TATT (0.48 vs 2.25 s) | `studies/euclid_dr3` |
| Four codes, Euclid DR3-like (13 bins, TATT + one-loop bias, 1 core) | cloelib fastest at every $n_\ell$: 3.5–16x faster than pyccl, 2.6–3.3x than CosmoSIS, 2.7–5x than former CLOE | `studies/euclid_dr3` |
| Does the CPU budget matter? | only for pyccl (OpenMP over ℓ): with 96–128 free cores it ties or beats cloelib from $n_\ell\approx500$. CosmoSIS and former CLOE are single-threaded; cloelib gains nothing at these sizes | `studies/euclid_dr1`, `studies/euclid_dr3` |
| Why did the July 2026 speedcheck find CLOE 2.5x (and 40x) faster? | its problem was tiny (10 bins, 20 ℓ, 100 $z$) and linear, so cloelib's eager-JAX overhead dominated; its cloelike ran CAMB 3x per call (fixed since); "no JAX" was `JAX_DISABLE_JIT=1`, a debugging mode | `studies/speedcheck_reanalysis` |
| One-off cost | cloelib compiles (JAX) on the first call at every new array shape: 2–5 s on 8 CPUs, up to 15 s on 1 core | all |
| Where does cloelib's time go? | at the analysis set-up 0.13 s (linear + NLA) / 0.39 s (one-loop + TATT) per evaluation, half or more of it in about 2,000 one-at-a-time JAX operations; with perturbation theory the cost grows with $n_\ell \times N_Z$, not with the number of spectra (6.0 s at $n_\ell = 3000$ for both 6 and 13 bins); CAMB outside the timed part costs about 5 s per cosmology | `studies/cloelib_profiling` |

## Layout

```
time_profiling/
├── README.md                     this file
├── tp_paths.py                   every location (external codes, envs, data, work) — env-var overridable
├── benchmarks/                   timing tools shared by the studies
│   ├── cloelib_benchmark.py        cloelib: one full 3x2pt from scratch (linear + NLA or one-loop + TATT)
│   ├── cloe_former_benchmark.py    former CLOE, run as a subprocess in the cloe-former env
│   └── cosmosis/                   the CosmoSIS 3x2pt pipeline (values and n(z) files go to work/)
├── studies/                      one folder per question, each: README.md, run.sh, notebook(s), results/
│   ├── cloelib_profiling/          cloelib alone: where the time goes, scaling, compilation, CPUs
│   ├── euclid_dr3/                 13 bins: four codes on 1 and 128 cores; former CLOE vs cloelib at the analysis set-up
│   ├── euclid_dr1/                 four codes, 6 bins, 8 and 96 CPUs
│   ├── speedcheck_reanalysis/      the July 2026 speedcheck, re-run and explained
│   └── _archive/early_exploration/ first exploration (September 2026), record only
├── data/                         inputs, on Zenodo (fetch_data.py)
├── environment/                  conda YAMLs, exact locks, set-up scripts, patches (README inside)
├── dashboard/                    the shared results dashboard: its datasets and page, built from the results
├── external/                     (git-ignored) code checkouts, by environment/setup_external.sh
└── work/                         (git-ignored) files the notebooks generate
```

## Set-up

```bash
cd time_profiling
bash environment/setup_external.sh                             # CLOE, CosmoSIS std. library, cloelib/cloelike versions (pinned)
python data/fetch_data.py                                      # inputs from Zenodo, checked against MANIFEST.sha256
bash environment/setup_external.sh                             # again: copies the speedcheck's CLOE configs (needs the data)
bash environment/setup_envs.sh                                 # conda envs, CosmoSIS build, Jupyter kernels
```

Every path can be redirected (`TP_EXTERNAL`, `TP_ENVS`, `TP_DATA`, `TP_WORK`; see `tp_paths.py`), for example to reuse existing environments. Each study has a `run.sh` that executes its notebook pinned with `taskset`.

## Conventions

- **What is timed.** Everything after the Boltzmann solver, with nothing cached between evaluations: each code's own interpolators, tracers and kernels, FAST-PT loops, Limber integrals. Every code gets the same n(z) arrays and the same number of redshift points.
- **Statistics.** The median of 3–5 evaluations. The first call at each array shape is reported separately, because for cloelib it includes JAX compilation.
- **Comparing results.** Ratios between codes within a study are what carry over. Absolute times depend on the machine. Each executed notebook starts with its host, date and CPU set.
- **CPU budgets.** Each run is pinned with `taskset`, with `OMP/MKL/OPENBLAS_NUM_THREADS` matching. The notebooks print the clock of their CPUs and warn below 1 GHz. In October 2026 `drontermeer`'s socket 0 ran at 400 MHz, which is why most runs use NUMA node 1. They also log the load average. Shared nodes need both checks.
- **Provenance.** External codes are pinned by commit in `environment/setup_external.sh`; the environments are locked in `environment/locks/`. The notebooks were executed in a working directory and moved here; only their path handling changed afterwards, and the spectra they compute were re-checked bit-identical in this layout.

## Data (Zenodo)

`data/` holds the inputs: the DR1 and DR3 n(z), and the July 2026 speedcheck's inputs and files. The payload (8 MB) lives on Zenodo; git tracks only `fetch_data.py`, `make_zenodo_bundle.sh`, `MANIFEST.sha256` and the README. Results (JSON, logs) are small and stay in git next to each notebook.
