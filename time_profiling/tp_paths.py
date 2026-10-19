"""Every location the time_profiling notebooks and scripts use, in one place.

Defaults assume the layout created by `environment/setup_external.sh`, `environment/setup_envs.sh` and
`data/fetch_data.py`. Each root can be overridden with an environment variable:

    TP_EXTERNAL  external code checkouts (CLOE, CosmoSIS standard library, cloelib/cloelike versions)
    TP_ENVS      conda environments (cloe-cosmosis, cloe-former)
    TP_DATA      benchmark input data (the Zenodo record)
    TP_WORK      files the notebooks generate (n(z) tables, CosmoSIS values files, temporary files)

Plain stdlib, so both environments (Python 3.12 and the Python 3.9 of cloe-former) can import it.
Notebooks import it with `sys.path.insert(0, <time_profiling dir>)`.
"""
import os
from pathlib import Path

TP = Path(__file__).resolve().parent                           # time_profiling/
EXTERNAL = Path(os.environ.get('TP_EXTERNAL', TP / 'external'))
ENVS = Path(os.environ.get('TP_ENVS', TP / 'environment' / 'envs'))
DATA = Path(os.environ.get('TP_DATA', TP / 'data'))
WORK = Path(os.environ.get('TP_WORK', TP / 'work'))

# ---------------------------------------------------------------- external codes (environment/setup_external.sh)
CLOE = EXTERNAL / 'cloe'                                       # former CLOE, archived main
CSL = EXTERNAL / 'cosmosis-standard-library'                   # + patches/csl_interpolation_cache_fix.patch
CLOELIB = {
    'pr596-c0f36e4': EXTERNAL / 'cloelib-pr596-c0f36e4',       # Euclid DR3 notebooks (non-linear bias, PR #596)
    'pr596-3f443c4': EXTERNAL / 'cloelib-pr596-3f443c4',       # Euclid DR1 notebooks (+ patches/cloelib_3f443c4...)
    '2026-06-691c4f3': EXTERNAL / 'cloelib-2026-06-691c4f3',   # the July 2026 speedcheck's cloelib
    'main-0966dfa': EXTERNAL / 'cloelib-main-0966dfa',         # 13-bin comparison, cloelib profiling, speedcheck today
    'main-a59f0a4': EXTERNAL / 'cloelib-main-a59f0a4',         # limber_z_convergence ("main" there)
}
CLOELIKE = {
    '2026-04-b8c8bdc': EXTERNAL / 'cloelike-2026-04-b8c8bdc',  # the July 2026 speedcheck's cloelike
    'main-2d240ea': EXTERNAL / 'cloelike-main-2d240ea',
}

# ---------------------------------------------------------------- Python environments (environment/setup_envs.sh)
PY_CLOE_COSMOSIS = ENVS / 'cloe-cosmosis' / 'bin' / 'python'   # cloelib, pyccl, CosmoSIS, Jupyter kernel
PY_CLOE_FORMER = ENVS / 'cloe-former' / 'bin' / 'python'       # former CLOE (Python 3.9, cobaya 3.3.1)

# ---------------------------------------------------------------- this repository
BENCHMARKS = TP / 'benchmarks'                                 # timing tools shared by the studies
STUDIES = TP / 'studies'
CLOE_FORMER_BENCHMARK = BENCHMARKS / 'cloe_former_benchmark.py'
CLOELIB_BENCHMARK = BENCHMARKS / 'cloelib_benchmark.py'
PIPELINE_INI = BENCHMARKS / 'cosmosis' / 'pipeline_3x2pt_tatt_nlbias.ini'

# ---------------------------------------------------------------- inputs (data/, Zenodo)
NZ_SPV3 = DATA / 'nz' / 'nzTabSPV3.fits'                       # 13 bins, Euclid DR3-like
NZ_DR1 = DATA / 'nz' / 'nz_example.fits'                       # 6 bins, Euclid DR1-like (= she-cal nzDR1like.fits)
SPEEDCHECK = DATA / 'speedcheck_2026-07'                       # inputs of the July 2026 speedcheck

# ---------------------------------------------------------------- generated
INI_WORK = WORK / 'cosmosis_ini'                               # n(z) tables and values files for CosmoSIS
TMP = WORK / 'tmp'


def cloe_photometric_dir(sample):
    """CLOE's data/<sample>/Photometric directory (created on demand; see cloe_former_benchmark.make_sample)."""
    path = CLOE / 'data' / sample / 'Photometric'
    path.mkdir(parents=True, exist_ok=True)
    return path


def check(*paths):
    """Fail early, with a pointer to the set-up step, if a required location is missing."""
    missing = [str(p) for p in paths if not Path(p).exists()]
    if missing:
        raise FileNotFoundError('Missing: ' + ', '.join(missing) + '. See time_profiling/README.md (Set-up) '
                                'or override TP_EXTERNAL / TP_ENVS / TP_DATA.')


for _d in (INI_WORK, TMP):
    _d.mkdir(parents=True, exist_ok=True)
