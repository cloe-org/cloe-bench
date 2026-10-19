# cloelib profiling

cloelib on its own: what one full photometric 3x2pt evaluation costs, where the time goes, and how it scales.

| file | what |
|---|---|
| `../../benchmarks/cloelib_benchmark.py` | one full evaluation from scratch, CAMB excluded, for `--model linear` (polynomial linear bias + NLA) or `--model pt` (one-loop bias + TATT), 6 or 13 bins, any $N_Z$ and $n_\ell$; `--breakdown` (time per stage), `--profile` (cProfile by library, eager JAX dispatch count). Also used by `../euclid_dr3` (CLOE vs cloelib) |
| `cloelib_profiling.ipynb` | where the time goes at the analysis set-up (13 bins, 32 ℓ, $N_Z = 600$); scaling with $N_Z$, $n_\ell$ and bins; JAX compilation per array shape; 1 / 8 / 96 CPUs; CAMB construction outside the timed part; known performance issues |
| `run.sh` | executes the notebook pinned to a CPU set (`CPUS=...`) |
| `results/` | outputs of the notebook (its figures go to `figures/`, not tracked) |

The accuracy side, how cloelib's C_ℓ converge with the number of redshift points, is in [`../../../numerical_validation/limber_z_convergence`](../../../numerical_validation/limber_z_convergence).

cloelib version: `main` at `0966dfa` (`tp_paths.CLOELIB['main-0966dfa']`), unless stated.
