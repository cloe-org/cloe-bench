# Environments and external codes

```bash
bash setup_external.sh     # clone CLOE, the CosmoSIS standard library and the cloelib/cloelike versions (pinned)
bash setup_envs.sh         # conda environments, CosmoSIS standard library build, Jupyter kernels
```

Both scripts are idempotent and follow `../tp_paths.py`: `TP_EXTERNAL` (default `../external/`) and `TP_ENVS` (default `envs/`).

## Environments

| environment | YAML | used for |
|---|---|---|
| `cloe-cosmosis` | `cloe-cosmosis-env-linux.yaml` | every notebook (Jupyter kernel `cloe-cosmosis`): cloelib, pyccl 3.3.6, CosmoSIS 3.25, CAMB 1.6.5, fast-pt 4.1, JAX 0.11.2 |
| `cloe-former` | `cloe-former-env-linux.yaml` | former CLOE, run as a subprocess: Python 3.9, numpy 1.23.5, CAMB 1.5.0, fast-pt 3.1.1, cobaya 3.3.1 |
| `cloelib-zconv` | `cloelib-zconv-env-linux.yaml` | `../numerical_validation/limber_z_convergence` (top level of cloe-bench) (kernel `cloelib-zconv`) |

`locks/` has `conda list` and `pip freeze` of the three environments the results were produced with. The YAML files leave a few packages unpinned, e.g. `euclidlib` (2026.10 in the runs).

## External codes (`setup_external.sh`)

| `tp_paths` key / directory | repository | commit | used by |
|---|---|---|---|
| `CLOE` → `cloe` | cloe-org/cloe (archived) | `1dd3660` | former CLOE in every comparison |
| `CSL` → `cosmosis-standard-library` | joezuntz/cosmosis-standard-library | `9e3dd611` + `patches/csl_interpolation_cache_fix.patch` | `euclid_dr3`, `euclid_dr1` |
| `CLOELIB['pr596-c0f36e4']` | cloe-org/cloelib, PR #596 (`refs/pull/596/head`) | `c0f36e4` | `euclid_dr3`; z-convergence `CLOELIB_SRC=384` |
| `CLOELIB['pr596-3f443c4']` | PR #596 | `a24ccff` + `patches/cloelib_3f443c4_from_a24ccff.patch` | `euclid_dr1` |
| `CLOELIB['2026-06-691c4f3']` | cloelib `main` | `691c4f3` (2026-06-09) | `speedcheck_reanalysis` (the speedcheck's cloelib) |
| `CLOELIB['main-0966dfa']` | cloelib `main` | `0966dfa` (2026-10-09) | `euclid_dr3` (CLOE vs cloelib), `cloelib_profiling`, `speedcheck_reanalysis` (today) |
| `CLOELIB['main-a59f0a4']` | cloelib `main` | `a59f0a4` | z-convergence `CLOELIB_SRC=main` |
| `CLOELIKE['2026-04-b8c8bdc']` | cloe-org/cloelike | `b8c8bdc` | `speedcheck_reanalysis` (the speedcheck's cloelike) |
| `CLOELIKE['main-2d240ea']` | cloelike `main` | `2d240ea` | `speedcheck_reanalysis` (today) |

**Patches.**
- `csl_interpolation_cache_fix.patch`: CosmoSIS's `project_2d` keys an interpolation cache on `id()`, which can return the wrong bin pair's P(k) for the non-linear-bias spectra. The fix is three lines.
- `cloelib_3f443c4_from_a24ccff.patch`: the Euclid DR1 runs used `3f443c4`, a local merge of `a24ccff` (PR #596, the redshift-quadrature / Simpson-weight / CAMB linear-P(k) fixes) with `main` (`a59f0a4`). Its conflict was resolved by hand and the merge was never pushed. The patch reproduces that exact tree on top of the published `a24ccff`, and `setup_external.sh` checks the resulting tree hash (`db61aaea`). The patch stays as uncommitted changes, so `git log` in that checkout, and the DR1 notebook's version line, show `a24ccff`.

Each notebook puts the cloelib version it needs first on `sys.path` and asserts that it is the one imported. The editable cloelib install in `cloe-cosmosis` only provides the dependencies.
