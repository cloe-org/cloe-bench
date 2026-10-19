"""Re-run the cloelike/cloelib photometric 3x2pt timing of the July 2026 speedcheck notebook.

Reproduces `speedcheck_cloe_cloelike_firecrown_withjax.ipynb`, sections "Build cloelike/cloelib likelihood"
and "Timing cloelike/cloelib using CAMB": same data files, same parameter point, same
Timed{Background,LinearPerturbations,NonLinearPerturbations} wrappers, same metric

    likelihood-only = full loglike time - (Background + LinPerturbations + NonLinPerturbations constructor time)

and the same N_REPEAT_CLOELIKE = 21 calls with the first one discarded. On top of that it records what the
likelihood-only time is made of:
  * how many ShearTracer / PositionsTracer objects are built per call, and their constructor time;
  * how many AngularTwoPoint.get_Cl calls are made, and their time;
  * a cProfile of one call, with self-time grouped by library.

Run it with the cloe-cosmosis python, once per (cloelib, cloelike) checkout:

    python cloelike_speedcheck.py --cloelib 2026-06-691c4f3 --cloelike 2026-04-b8c8bdc --out june.json
--cloelib / --cloelike are keys of tp_paths.CLOELIB / tp_paths.CLOELIKE, or paths to checkouts.

--clear-cache: the current cloelike (since gh-159) caches background, perturbations and tracers per cosmology,
so repeated calls at one fixed point would only time cache hits. With this flag the caches are emptied before
every call, so each call is a full evaluation at a new point, as in a sampler.
"""
import argparse
import cProfile
import json
import os
import pstats
import sys
import time
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))   # time_profiling/, for tp_paths
import tp_paths  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cloelib', required=True)
    ap.add_argument('--cloelike', required=True)
    ap.add_argument('--repeat', type=int, default=21)       # N_REPEAT_CLOELIKE in the speedcheck
    ap.add_argument('--clear-cache', action='store_true')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    cloelib_dir = os.path.abspath(tp_paths.CLOELIB.get(args.cloelib, args.cloelib))
    cloelike_dir = os.path.abspath(tp_paths.CLOELIKE.get(args.cloelike, args.cloelike))
    data_dir = str(tp_paths.SPEEDCHECK / 'inputs')
    tp_paths.check(cloelib_dir, cloelike_dir, data_dir)
    for path in (cloelike_dir, cloelib_dir):
        sys.path.insert(0, path)
    import cloelib
    import cloelike
    import jax
    assert cloelib.__file__.startswith(cloelib_dir), cloelib.__file__
    assert cloelike.__file__.startswith(cloelike_dir), cloelike.__file__

    import euclidlib as el
    from cloelib.cosmology.camb_cosmology import (CAMBBackground, CAMBLinearPerturbations,
                                                  CAMBNonLinearPerturbations)
    from cloelib.summary_statistics.angular_two_point import AngularTwoPoint
    import cloelike.EuclidLikelihood_photo_Cls as like_mod
    from cloelike.EuclidLikelihood_photo_Cls import EuclidLikelihood_3x2pt

    # ---------------------------------------------------------------- data: as in the speedcheck, cell 10
    a = np.loadtxt(os.path.join(data_dir, 'niTab-EP10-RB00.dat'))
    z_fine, nz_fine = a[:, 0], a[:, 1:11].T
    mask_z = z_fine > 0.0
    z_fine, nz_fine = z_fine[mask_z], nz_fine[:, mask_z]
    nz_fine_norm = nz_fine / np.trapezoid(nz_fine, z_fine, axis=1)[:, None]
    z_nz = np.linspace(z_fine[0], z_fine[-1], 100)
    nz_coarse = np.array([np.interp(z_nz, z_fine, n, left=0.0, right=0.0) for n in nz_fine_norm])
    nz_coarse_norm = nz_coarse / np.trapezoid(nz_coarse, z_nz, axis=1)[:, None]

    cells_data = dict(el.le3.pk_wl.angular_power_spectra(os.path.join(data_dir, 'Cls_from_dat_WLPSPP.fits')))
    ells = cells_data[('SHE', 'SHE', 1, 1)].ell
    for key, arr in list(cells_data.items()):
        if key[:2] == ('SHE', 'SHE'):
            arr = np.asarray(arr)
            if arr.shape == (2, 20):
                patched = np.zeros((2, 2, 20), dtype=arr.dtype)
                patched[0, 0, :], patched[1, 1, :] = arr[0, :], arr[1, :]
                cells_data[key] = patched

    def perm_block(n_ell, n_pair):
        return np.array([ell * n_pair + pair for pair in range(n_pair) for ell in range(n_ell)])

    perm = np.concatenate([perm_block(20, 55), 55 * 20 + perm_block(20, 100), 155 * 20 + perm_block(20, 55)])
    with np.load(os.path.join(data_dir, 'CovMat-3x2pt-Gauss-20Bins.npz')) as f:
        full_cov = f['arr_0'][np.ix_(perm, perm)]
    # The speedcheck also passes the 154 MB mixing matrix, but mode=None never uses it (no pseudo-C_ell).
    data = {'cells': cells_data, 'ells': ells, 'z_arr': z_nz, 'cov': full_cov,
            'dndz_pos': nz_coarse_norm, 'dndz_she': nz_coarse_norm}
    settings = {'n_ell_bins': 20, 'scale_cuts': {key: [0, np.inf] for key in cells_data}}

    pars = {'H0': 67, 'Omega_cdm0': 0.27, 'Omega_b0': 0.049, 'ns': 0.96, 'As': 2.1e-9, 'w0': -1, 'wa': 0,
            'Omega_k0': 0, 'mnu': 0.0000001, 'gamma_MG': 0.545, 'N_mnu': 1, 'log10TAGN': 7.75,
            'AIA': 0.16, 'EtaIA': 1.66, 'CIA': 0.0134, 'b1_photo_poly0': 1.33291, 'b1_photo_poly1': -0.72414,
            'b1_photo_poly2': 1.0183, 'b1_photo_poly3': -0.14913, 'alpha_s': 0.0}
    for i in range(1, 11):
        pars.update({f'magnification_bias_{i}': 0.0, f'dz_pos_{i}': 0.0, f'width_pos_{i}': 1.0,
                     f'multiplicative_bias_{i}': 0.0, f'dz_shear_{i}': 0.0, f'width_shear_{i}': 1.0})

    # ---------------------------------------------------------------- the speedcheck's timing wrappers (cell 16)
    timers = {'bg': [0.0, 0], 'lp': [0.0, 0], 'nlp': [0.0, 0], 'she_tracer': [0.0, 0], 'pos_tracer': [0.0, 0],
              'get_Cl': [0.0, 0]}

    def proxy(cls, name, **extra):
        class Timed:
            def __init__(self, *a, **kw):
                kw.update(extra)
                t0 = time.perf_counter()
                self._obj = cls(*a, **kw)
                timers[name][0] += time.perf_counter() - t0
                timers[name][1] += 1

            def __getattr__(self, attr):
                return getattr(self._obj, attr)

            def sigma8_0(self):
                s = getattr(self._obj, 'sigma8_0')
                return s() if callable(s) else s
        return Timed

    def count_init(cls, name):   # tracers: time the constructor in place (get_Cl dispatches on the exact class)
        orig = cls.__init__

        def __init__(self, *a, **kw):
            t0 = time.perf_counter()
            orig(self, *a, **kw)
            timers[name][0] += time.perf_counter() - t0
            timers[name][1] += 1
        cls.__init__ = __init__

    from cloelib.observables.photo import ShearTracer, PositionsTracer
    count_init(ShearTracer, 'she_tracer')
    count_init(PositionsTracer, 'pos_tracer')
    _get_Cl = AngularTwoPoint.get_Cl

    def get_Cl(self, *a, **kw):
        t0 = time.perf_counter()
        out = _get_Cl(self, *a, **kw)
        timers['get_Cl'][0] += time.perf_counter() - t0
        timers['get_Cl'][1] += 1
        return out
    AngularTwoPoint.get_Cl = get_Cl

    like = EuclidLikelihood_3x2pt(
        data=data, settings=settings, Background=proxy(CAMBBackground, 'bg'),
        LinPerturbations=proxy(CAMBLinearPerturbations, 'lp'),
        NonLinPerturbations=proxy(CAMBNonLinearPerturbations, 'nlp', nonlinear_model='mead2020_feedback'),
        mode=None)

    def one_call():
        if args.clear_cache:
            for attr in ('_perturbations_cache', '_pos_tracer_cache', '_she_tracer_cache'):
                if hasattr(like, attr):
                    delattr(like, attr)
        for v in timers.values():
            v[0], v[1] = 0.0, 0
        t0 = time.perf_counter()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            val = like.loglike(pars)
        full = time.perf_counter() - t0
        rec = {'full': full, 'loglike': float(val), **{f'{k}_s': v[0] for k, v in timers.items()},
               **{f'{k}_n': v[1] for k, v in timers.items()}}
        rec['likelihood_only'] = full - rec['bg_s'] - rec['lp_s'] - rec['nlp_s']   # the speedcheck's metric
        return rec

    calls = []
    for i in range(args.repeat):
        calls.append(one_call())
        c = calls[-1]
        print(f'call {i + 1:2d}/{args.repeat}: full {c["full"]:7.3f} s | likelihood-only {c["likelihood_only"]:.3f} s | '
              f'tracers she {c["she_tracer_n"]}x {c["she_tracer_s"]:.3f} s, pos {c["pos_tracer_n"]}x '
              f'{c["pos_tracer_s"]:.3f} s | get_Cl {c["get_Cl_n"]}x {c["get_Cl_s"]:.3f} s | '
              f'constructors bg/lp/nlp {c["bg_n"]}/{c["lp_n"]}/{c["nlp_n"]}', flush=True)

    # cProfile of one more call: self-time by library, likelihood-only part (constructor frames excluded)
    prof = cProfile.Profile()
    prof.enable()
    prof_call = one_call()
    prof.disable()
    st = pstats.Stats(prof)
    groups = {}
    for (fname, _, func), (_, _, tottime, _, _) in st.stats.items():
        key = ('jax/xla' if ('/jax/' in fname or '/jaxlib/' in fname) else
               'camb' if '/camb/' in fname else
               'fastpt' if '/fastpt/' in fname else
               'cloelib' if '/cloelib/' in fname and 'cosmology' not in fname else
               'cloelib cosmology (CAMB wrappers)' if '/cloelib/' in fname else
               'cloelike' if '/cloelike/' in fname else
               'numpy/scipy' if ('/numpy/' in fname or '/scipy/' in fname) else
               'builtins/C' if fname == '~' else 'other python')
        groups[key] = groups.get(key, 0.0) + tottime
    top = []
    for (fname, line, func), (cc, nc, tottime, cumtime, _) in sorted(st.stats.items(), key=lambda x: -x[1][2])[:20]:
        ext = str(tp_paths.EXTERNAL)
        top.append([f'{os.path.relpath(fname, ext) if fname.startswith(ext) else fname}:{line}({func})',
                    nc, round(tottime, 4), round(cumtime, 4)])

    used = calls[1:]   # the speedcheck discards the first call
    out = {'cloelib': cloelib.__file__, 'cloelike': cloelike.__file__, 'jax': jax.__version__,
           'jax_disable_jit': os.environ.get('JAX_DISABLE_JIT', '0'), 'clear_cache': args.clear_cache,
           'n_cpu': len(os.sched_getaffinity(0)), 'calls': calls,
           'median': {k: float(np.median([c[k] for c in used])) for k in used[0]},
           'profile_groups': groups, 'profile_total': st.total_tt, 'profile_call': prof_call, 'profile_top': top}
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1)
    m = out['median']
    print(f'\nmedian of calls 2-{args.repeat}: full {m["full"]:.3f} s, likelihood-only {m["likelihood_only"]:.3f} s')
    print('profile (self time, one call): ' + ', '.join(f'{k} {v:.3f}s' for k, v in sorted(groups.items(), key=lambda x: -x[1])))
    print('written', args.out)


if __name__ == '__main__':
    main()
