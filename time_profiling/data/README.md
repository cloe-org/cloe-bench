# Input data of `time_profiling` (Zenodo)

The inputs the time-profiling notebooks read. The files live in a Zenodo record, not in git; this folder holds the tooling, and the payload is git-ignored.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23480065.svg)](https://doi.org/10.5281/zenodo.23480065)

**Zenodo:** [https://zenodo.org/records/23480065](https://zenodo.org/records/23480065), DOI [`10.5281/zenodo.23480065`](https://doi.org/10.5281/zenodo.23480065) (this version; all versions: [`10.5281/zenodo.23479921`](https://doi.org/10.5281/zenodo.23479921)). `fetch_data.py` downloads `time_profiling_data_v1.tar.gz` from it.

```bash
cd time_profiling/data
python fetch_data.py            # download, extract here, verify against MANIFEST.sha256
python fetch_data.py --verify-only
```

Another location can be used with `TP_DATA=/path` (see `time_profiling/tp_paths.py`).

## Contents (`time_profiling_data_v1.tar.gz`, 7.1 MB, 5 files)

| path | used by | what |
|---|---|---|
| `nz/nzTabSPV3.fits` | `euclid_dr3`, `cloelib_profiling` | 13 tomographic bins, Euclid DR3-like (SPV3) |
| `nz/nz_example.fits` | `euclid_dr1`, `cloelib_profiling` | 6 tomographic bins, Euclid DR1-like; identical to `she-cal/synthetic_data/nzDR1like.fits` and to the n(z) of `cloe-org/RunningChains/3x2pt_DR1_like.py` |
| `speedcheck_2026-07/inputs/` | `speedcheck_reanalysis` | the inputs of the July 2026 CLOE / cloelike / Firecrown speedcheck: the 10-bin n(z) `niTab-EP10-RB00.dat`, the data vector `Cls_from_dat_WLPSPP.fits` and the covariance `CovMat-3x2pt-Gauss-20Bins.npz` (CLOE's synthetic benchmark products, reformatted by the speedcheck author) |

**Not included:**
- **The speedcheck's own notebooks, configs and code** (its CLOE configs, modified `photo.py`, cloelike likelihood file and path files). They are not public. `studies/speedcheck_reanalysis` reads them from `tp_paths.SPEEDCHECK_FILES` (see its README); no other study needs them.
- **The speedcheck's spectroscopic covariances and its 148 MB identity mixing matrix.** The re-analysis uses neither: its likelihood runs with `mode=None`, so the mixing matrix is never applied.
- **The data vectors and covariances of CLOE's own samples.** `benchmarks/cloe_former_benchmark.py` builds those from CLOE's repository data (`make_sample`), with placeholders, because the timed theory evaluation never reads them.

## Making a new version

```bash
bash make_zenodo_bundle.sh v2     # -> time_profiling_data_v2.tar.gz + refreshed MANIFEST.sha256
```

Upload the archive as a new version of the Zenodo record, then commit `MANIFEST.sha256` together with the new `ZENODO_URL` and DOI.
