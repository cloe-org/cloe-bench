# The July 2026 speedcheck, re-run

**Question.** Why did the speedcheck shared in July 2026 find former CLOE 2.5x faster than cloelike/cloelib (and 40x faster "without JAX"), when the other studies find the opposite?

**Set-up.** The speedcheck's own set-up and files (in the Zenodo record, `../../data/speedcheck_2026-07/`): 10 bins, 20 ℓ values, 100 redshift points, linear bias + NLA. It is re-run on 8 CPUs, then changed one thing at a time.

**Headline.** The 2.5x is reproduced (2.1x). It has two causes: on such a small problem, cloelib's per-operation JAX overhead dominates, and the June 2026 cloelike ran CAMB 3 times per call (fixed since). The "no JAX" run was `JAX_DISABLE_JIT=1`, a debugging mode that still runs JAX, one operation at a time.

| file | what |
|---|---|
| `speedcheck_reanalysis.ipynb` | the analysis |
| `cloe_speedcheck.py`, `cloelike_speedcheck.py` | the speedcheck's timing of each code, reproduced as scripts, with a breakdown of the likelihood-only time |
| `run.sh` | executes the notebook pinned to a CPU set (`CPUS=...`, 48-55 by default) |
| `results/` | outputs (figures go to `figures/`, not tracked) |

Versions: see the provenance table in [`../README.md`](../README.md).
