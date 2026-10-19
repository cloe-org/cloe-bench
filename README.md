<p align="center">
  <img src="docs/cloe-bench.png" alt="cloe-bench logo" width="500">
</p>


**Scientific validation of cloelib and cloelike observables**  Compute validation benchmarks to test the scientific accuracy and speed of cloelib and cloelike for cosmological analyses purposes

## Modules

| module | what |
|---|---|
| [`time_profiling/`](time_profiling) | time profiling of cloelib on its own and against former CLOE, pyccl and CosmoSIS ([`studies/`](time_profiling/studies)) and the shared timing tools ([`benchmarks/`](time_profiling/benchmarks)); input data on Zenodo |
| [`numerical_validation/`](numerical_validation) | numerical validation of cloelib: redshift convergence of its Limber $C_\ell$ ([`limber_z_convergence/`](numerical_validation/limber_z_convergence)); uses `time_profiling/`'s paths, environments and data |
