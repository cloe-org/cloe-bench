# Euclid DR1-like: cloelib vs pyccl vs CosmoSIS vs former CLOE, laptop vs node

**Question.** The `euclid_dr3` comparison for a DR1-like set-up. Does the CPU budget change the ranking?

**Set-up.** 6 bins (`nz_example.fits`), 78 spectra, the same model and protocol as `euclid_dr3`. Run on 8 CPUs (a laptop) and on 96 CPUs (NUMA node 1 of `drontermeer`).

**Headline.** On 8 CPUs cloelib is the fastest code at every $n_\ell$. Only pyccl uses the extra CPUs, and on 96 CPUs it overtakes cloelib from $n_\ell \approx 500$.

| file | what |
|---|---|
| `time_comparison_Euclid_DR1.ipynb` | the study, executed on 96 CPUs; its section 4.1 compares both budgets |
| `time_comparison_Euclid_DR1_8cpu.ipynb` | the same notebook, executed on 8 CPUs |
| `run.sh` | executes both runs: 8 CPUs, then the full budget (`CPUS_8=...`, `CPUS_FULL=...`) |
| `results/` | outputs, labelled `_8cpu` / `_96cpu` (figures go to `figures/`, not tracked) |

Versions: see the provenance table in [`../README.md`](../README.md).
