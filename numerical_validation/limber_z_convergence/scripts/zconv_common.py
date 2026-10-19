"""Shared set-up for the cloelib redshift-convergence investigation.

The question: in `studies/euclid_dr3/time_comparison_Euclid_DR3.ipynb` cloelib's
C_ell converge erratically with the number of redshift points N_Z, for one spectrum
in particular (GG for the narrowest, lowest-z SPV3 bin), while pyccl / CosmoSIS /
former CLOE converge smoothly on the same n(z) arrays.

This module builds that set-up with the two redshift grids cloelib uses decoupled:
  * the *tracer* grid ``z_t`` (n(z), window functions, Limber integral), any size;
  * the *perturbation* grid ``z_p`` (CAMB P(k,z), FAST-PT growth), at most 255
    points because CAMB accepts at most 256 redshifts (cloelib adds z = 0).
cloelib interpolates P(k,z) from ``z_p`` onto ``z_t`` (akima in log P), so the
Limber/window quadrature can be converged well past the CAMB cap.

It also provides drop-in replacements, applied by monkeypatching module attributes
(cloelib itself is not edited):
  * ``set_quadrature('trapezoid')``: Limber weights (``simpsons_weights_jit`` in
    angular_two_point) and window weights (``cached_stacked_simpson`` in
    positions / shear) -> trapezoid rule on the same nodes;
  * ``set_signed_interp('linear_p')``: interpolate signed effective spectra (TATT,
    non-linear bias) in P instead of in log|P| + sign.

Which cloelib is used is chosen with the environment variable ``CLOELIB_SRC``:
  * unset / ``main``: cloelib main at a59f0a4 (tp_paths.CLOELIB['main-a59f0a4']);
  * ``384``: the non-linear galaxy bias branch, PR #596 at c0f36e4 (tp_paths.CLOELIB['pr596-c0f36e4']);
  * any other value: the path of a cloelib checkout (used to verify fixes).
"""

import os
import sys
from pathlib import Path

import numpy as np
from scipy import integrate

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'time_profiling'))   # cloe-bench/time_profiling/, for tp_paths
import tp_paths  # noqa: E402

CLOELIB_SRC = os.environ.get('CLOELIB_SRC', 'main')
if CLOELIB_SRC in ('main', '384'):
    _src = tp_paths.CLOELIB['main-a59f0a4' if CLOELIB_SRC == 'main' else 'pr596-c0f36e4']
else:   # any other value: path to a cloelib checkout (e.g. one with fixes)
    _src = Path(CLOELIB_SRC).resolve()
    CLOELIB_SRC = 'path-' + _src.name
tp_paths.check(_src, tp_paths.NZ_SPV3)
sys.path.insert(0, str(_src))

import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402

import cloelib  # noqa: E402

assert Path(cloelib.__file__).resolve().is_relative_to(_src.resolve()), \
    f'wrong cloelib imported: {cloelib.__file__} (expected under {_src})'

from cloelib.cosmology.camb_cosmology import (  # noqa: E402
    CAMBBackground, CAMBLinearPerturbations, CAMBNonLinearPerturbations)
from cloelib.observables.photo import PositionsTracer, ShearTracer  # noqa: E402
from cloelib.observables.photo.shear import PBJTATTLoopComputer  # noqa: E402
from cloelib.summary_statistics import angular_two_point as a2p  # noqa: E402
from cloelib.observables.photo import positions as _positions, shear as _shear  # noqa: E402
from cloelib.auxiliary import math_utils  # noqa: E402

HAS_NLBIAS = hasattr(_positions, 'PBJNonlinearBiasLoopComputer')
if HAS_NLBIAS:
    from cloelib.observables.photo.positions import PBJNonlinearBiasLoopComputer  # noqa: E402

jax.config.update('jax_enable_x64', True)

# ---------------------------------------------------------------- inputs
ZMIN, ZMAX = 1e-4, 3.0
COSMO = dict(H0=70.0, Omega_c=0.25, Omega_b=0.05, ns=0.96, As=2e-9, mnu=0.06)
AIA, CIA, EtaIA, A2IA, Eta2IA, bTA, z0IA = 1.72, 0.0134, -0.41, 0.40, 2.69, -0.83, 0.62
B1, B2, BS, B3NL, BK2 = 1.0, 0.5, -0.3, 0.2, 0.1
ELLS = np.geomspace(2, 2999, 32)
CHECKS = [('GG', 0, 0), ('GG', 6, 6), ('GE', 2, 10), ('EE', 0, 0), ('EE', 6, 12), ('EE', 12, 12)]
CHECK_KEYS = [f'{p}_{i + 1}_{j + 1}' for p, i, j in CHECKS]
MODELS = {   # name -> (galaxy bias, IA)
    'linear_NLA': ('poly', 'NLA'),
    'linear_TATT': ('poly', 'TATT'),
    'nlbias_NLA': ('nonlinear', 'NLA'),
    'nlbias_TATT': ('nonlinear', 'TATT'),   # the model of time_comparison_Euclid_DR3.ipynb
}


def load_native_nz():
    import euclidlib as el
    z_all, nz_all = el.phz.redshift_distributions(str(tp_paths.NZ_SPV3))
    sel = z_all <= ZMAX
    z = z_all[sel]
    return z, np.vstack([v[sel] / integrate.trapezoid(v[sel], z) for v in nz_all.values()])


Z_NATIVE, NZ_NATIVE = load_native_nz()
N_BINS = NZ_NATIVE.shape[0]


def tracer_nz(z_t):
    """n(z) on the tracer grid: linear resampling + trapezoid renormalisation (as in the notebook)."""
    nz = np.vstack([np.interp(z_t, Z_NATIVE, n) for n in NZ_NATIVE])
    return nz / integrate.trapezoid(nz, z_t, axis=1)[:, None]


# ---------------------------------------------------------------- cosmology
def make_background():
    return CAMBBackground(H0=COSMO['H0'], Omega_cdm0=COSMO['Omega_c'], Omega_b0=COSMO['Omega_b'],
                          w0=-1.0, wa=0.0, Omega_k0=0.0, ns=COSMO['ns'], As=COSMO['As'],
                          mnu=COSMO['mnu'], N_mnu=1, gamma_MG=0.545)


class CachedCAMBLinearPerturbations(CAMBLinearPerturbations):
    """P_lin interpolated from the CAMB run done in __init__ (the stock class re-runs CAMB on every call)."""

    def __init__(self, background, redshifts):
        super().__init__(background, redshifts)
        self._pk_interp = self.results.get_matter_power_interpolator(
            nonlinear=False, hubble_units=False, k_hunit=False, extrap_kmax=self.kmax,
            var1='delta_tot', var2='delta_tot')

    def matter_power_spectrum(self, zs, ks, hubble_units=False, k_hunit=False):
        return self._pk_interp.P(zs, ks)


_PERT_CACHE = {}


def perturbations(n_p):
    """CAMB non-linear + linear perturbations on z_p = linspace(ZMIN, ZMAX, n_p) (cached)."""
    if n_p not in _PERT_CACHE:
        assert n_p <= 255, 'CAMB accepts at most 256 redshifts (cloelib adds z = 0)'
        z_p = np.linspace(ZMIN, ZMAX, n_p)
        nl = CAMBNonLinearPerturbations(make_background(), None, z_p, nonlinear_model='mead2020')
        lin = CachedCAMBLinearPerturbations(make_background(), z_p)
        _PERT_CACHE[n_p] = (nl, lin)
    return _PERT_CACHE[n_p]


# ---------------------------------------------------------------- tracers and spectra
def _nuisance(n_bins):
    pos_poly = {'b1_photo_poly0': B1, 'b1_photo_poly1': 0.0, 'b1_photo_poly2': 0.0, 'b1_photo_poly3': 0.0}
    pos_nl = {**{f'b1_photo_nl_bin{i}': B1 for i in range(n_bins)},
              **{f'b2_photo_nl_bin{i}': B2 for i in range(n_bins)},
              **{f'bs2_photo_nl_bin{i}': BS for i in range(n_bins)},
              **{f'b3nl_photo_nl_bin{i}': B3NL for i in range(n_bins)},
              **{f'bk2_photo_nl_bin{i}': BK2 for i in range(n_bins)}}
    pos_common = {**{f'magnification_bias_{i}': 0.0 for i in range(1, n_bins + 1)},
                  **{f'dz_pos_{i}': 0.0 for i in range(1, n_bins + 1)},
                  **{f'width_pos_{i}': 1.0 for i in range(1, n_bins + 1)}}
    she = {'AIA': AIA, 'CIA': CIA, 'EtaIA': EtaIA, 'A2IA': A2IA, 'bTA': bTA, 'Eta2IA': Eta2IA, 'z0IA': z0IA,
           **{f'multiplicative_bias_{i}': 0.0 for i in range(1, n_bins + 1)},
           **{f'dz_shear_{i}': 0.0 for i in range(1, n_bins + 1)},
           **{f'width_shear_{i}': 1.0 for i in range(1, n_bins + 1)}}
    return {**pos_poly, **pos_common}, {**pos_nl, **pos_common}, she


NUIS_POS_POLY, NUIS_POS_NL, NUIS_SHE = _nuisance(N_BINS)


class NoSig4LoopComputer:
    """PBJNonlinearBiasLoopComputer with the sigma^4 kernel set to zero (the CosmoSIS / Pandey et al.
    convention; same wrapper as validation_cosmosis_nonlinear_bias.ipynb)."""

    def __init__(self, inner):
        self.inner = inner

    def compute(self, name):
        f = self.inner.compute(name)
        if name != 'nlbias_sig4':
            return f
        return lambda matter_pk, ks, zs: jnp.zeros_like(f(matter_pk, ks, zs))


SUBTRACT_SIG4 = True   # set False to zero cloelib's sigma^4 kernel (E6)


def build_tracers(model, n_t, n_p):
    bias, ia = MODELS[model]
    if bias == 'nonlinear' and not HAS_NLBIAS:
        raise RuntimeError(f'{model} needs the non-linear bias branch: run with CLOELIB_SRC=384')
    nl, lin = perturbations(n_p)
    z_t = np.linspace(ZMIN, ZMAX, n_t)
    nz = tracer_nz(z_t)
    if bias == 'poly':
        pos = PositionsTracer(perturbations=nl, dndz=nz, z=z_t, galaxy_bias_model='poly',
                              nuisance_params=NUIS_POS_POLY)
    else:
        pos = PositionsTracer(perturbations=nl, dndz=nz, z=z_t, galaxy_bias_model='nonlinear',
                              nuisance_params=NUIS_POS_NL,
                              nl_bias_loop_computer=(PBJNonlinearBiasLoopComputer(lin) if SUBTRACT_SIG4
                                                     else NoSig4LoopComputer(PBJNonlinearBiasLoopComputer(lin))))
    kw = dict(tatt_loop_computer=PBJTATTLoopComputer(lin)) if ia == 'TATT' else {}
    she = ShearTracer(perturbations=nl, dndz=nz, z=z_t, nuisance_params=NUIS_SHE, ia_model=ia, **kw)
    return pos, she, nl


def check_spectra(model, n_t, n_p, ells=ELLS):
    """The six check spectra (E-mode parts), as {key: array over ells}."""
    pos, she, nl = build_tracers(model, n_t, n_p)
    cl = {}
    for t1, t2 in ((pos, pos), (pos, she), (she, she)):
        cl.update(a2p.AngularTwoPoint(t1, t2).get_Cl(ells, 0, nl.k))
    names = {'GG': ('POS', 'POS'), 'GE': ('POS', 'SHE'), 'EE': ('SHE', 'SHE')}
    out = {}
    for (p, i, j), key in zip(CHECKS, CHECK_KEYS):
        arr = np.asarray(cl[(*names[p], i + 1, j + 1)].array)
        out[key] = arr if p == 'GG' else arr[0] if p == 'GE' else arr[0, 0]
    return out


# ---------------------------------------------------------------- swappable numerics
_ORIG = dict(limber=a2p.simpsons_weights_jit,
             win_pos=_positions.cached_stacked_simpson,
             win_she=_shear.cached_stacked_simpson,
             signed=a2p.Pkl_interp_signed_vmap,
             signed_terms=getattr(a2p, 'Pkl_interp_signed_vmap_terms', None))


def trapezoid_weights(n):
    w = np.ones(n)
    w[0] = w[-1] = 0.5
    return jnp.asarray(w)


def stacked_trapezoid(n):
    """Row i: zeros for the first i nodes, trapezoid weights on nodes i..n-1 (the stacked-Simpson analogue)."""
    w = np.zeros((n, n))
    for i in range(n - 1):
        w[i, i:] = 1.0
        w[i, i] = w[i, -1] = 0.5
    return jnp.asarray(w)


def _clear_jit_caches():
    # cloelib's jitted functions capture these module attributes when first traced, so a swap only
    # takes effect after JAX's caches are cleared. cached_stacked_simpson's lru_cache must be cleared
    # with them (it caches a tracer; see the cloelib lru_cache-in-jit issue).
    jax.clear_caches()
    if hasattr(math_utils, '_cached_stacked_simpson_py'):
        math_utils._cached_stacked_simpson_py.cache_clear()


def set_quadrature(kind):
    """'simpson' (cloelib default) or 'trapezoid', for both the Limber integral and the window functions."""
    _clear_jit_caches()
    if kind == 'simpson':
        a2p.simpsons_weights_jit = _ORIG['limber']
        _positions.cached_stacked_simpson = _ORIG['win_pos']
        _shear.cached_stacked_simpson = _ORIG['win_she']
    elif kind == 'trapezoid':
        a2p.simpsons_weights_jit = trapezoid_weights
        _positions.cached_stacked_simpson = stacked_trapezoid
        _shear.cached_stacked_simpson = stacked_trapezoid
    else:
        raise ValueError(kind)


def _pkl_interp_linear_p(k_l, z_l, ks, zs, Pk):
    import interpax
    log_ks = jnp.log10(ks)
    log_k = jnp.clip(jnp.log10(k_l), log_ks.min(), log_ks.max())
    return interpax.interp2d(log_k, z_l, log_ks, zs, Pk, method='akima', extrap=True)


_pkl_interp_linear_p_vmap = jax.jit(jax.vmap(_pkl_interp_linear_p, in_axes=(0, None, None, None, None)))
# the 384 branch's batched version over PkTerms (non-linear bias): built at import from the *object*
# Pkl_interp_signed_vmap, so it must be replaced separately
_pkl_interp_linear_p_vmap_terms = jax.jit(jax.vmap(_pkl_interp_linear_p_vmap, in_axes=(None, None, None, None, 0)))


def set_signed_interp(kind):
    """'logabs' (cloelib default: akima in log10|P| and in sign) or 'linear_p' (akima in P)."""
    _clear_jit_caches()
    a2p.Pkl_interp_signed_vmap = _ORIG['signed'] if kind == 'logabs' else _pkl_interp_linear_p_vmap
    if _ORIG['signed_terms'] is not None:
        a2p.Pkl_interp_signed_vmap_terms = (_ORIG['signed_terms'] if kind == 'logabs'
                                            else _pkl_interp_linear_p_vmap_terms)


def stacked_weights_report(n=6):
    """cloelib's stacked Simpson weight matrix for a small grid, vs the exact sums of a constant integrand."""
    w = np.asarray(math_utils.stacked_simpson(n))
    return w, w.sum(axis=1), np.arange(n - 1, -1, -1, dtype=float)   # row i should integrate 1 over (n-1-i) steps
