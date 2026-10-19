"""cloelib timing: one full photometric 3x2pt evaluation from scratch, CAMB excluded.

Used by studies/cloelib_profiling and studies/euclid_dr3 (time_comparison_cloe_vs_cloelib_13bins.ipynb).

n(z): the 13 SPV3 bins (--n-bins 13, Euclid DR3-like) or the 6 DR1-like bins (--n-bins 6), cut at --z-max and
renormalised. Cosmology and nuisance values of time_comparison_Euclid_DR3.ipynb. Two models:
  * --model linear: galaxy bias "poly" (cubic in z, the July 2026 speedcheck's choice) + NLA intrinsic alignments;
  * --model pt:     one-loop galaxy bias ("nonlinear", PBJ loop computer) + TATT (PBJ loop computer).
Timed per evaluation: fresh tracers, fresh loop computers, the perturbations' P(k) interpolator caches emptied,
and AngularTwoPoint.get_Cl x3 (GG, GE, EE); the CAMB runs behind CAMB*Perturbations are not timed.
Redshift grids: --n-z points for n(z), kernels and the Limber integral, uniform on [1e-4, --z-max]; the CAMB
P(k, z) grid has min(--n-z, --n-z-pk) points (CAMB accepts at most 256 redshifts). cloelib evaluates P(k) on the
perturbations' grid and the Limber integral on the tracers' grid.

Extra diagnostics:
  --breakdown  per-stage medians of the same evaluation: tracers (incl. loop computers), get_Cl GG / GE / EE;
  --profile    cProfile of one evaluation (first --n-z and --nell): self time grouped by library, and the number
               of eager JAX primitive dispatches (operations executed outside any jax.jit).

Run with the cloe-cosmosis python (tp_paths.PY_CLOE_COSMOSIS):
    python cloelib_benchmark.py --cloelib main-0966dfa --model pt --n-z 600 --nell 32 --out x.json
--cloelib is a key of tp_paths.CLOELIB or a path to a cloelib checkout.
"""
import argparse
import copy
import cProfile
import json
import os
import pstats
import sys
import time
import timeit
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..')))   # time_profiling/, for tp_paths
import tp_paths  # noqa: E402


def profile_groups(stats):
    groups, n_dispatch = {}, 0
    for (fname, _, func), (_, ncalls, tottime, _, _) in stats.stats.items():
        key = ('JAX/XLA' if ('/jax/' in fname or '/jaxlib/' in fname) else
               'FAST-PT' if '/fastpt/' in fname else
               'CAMB library calls' if '/camb/' in fname else
               'cloelib' if '/cloelib/' in fname else
               'NumPy/SciPy' if ('/numpy/' in fname or '/scipy/' in fname) else
               'builtins / C' if fname == '~' else 'other Python')
        groups[key] = groups.get(key, 0.0) + tottime
        if fname.endswith('jax/_src/dispatch.py') and func == 'apply_primitive':
            n_dispatch += ncalls
    return groups, n_dispatch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cloelib', required=True)
    ap.add_argument('--model', choices=('linear', 'pt'), required=True)
    ap.add_argument('--n-bins', type=int, choices=(6, 13), default=13)
    ap.add_argument('--nell', type=int, nargs='+', default=[32])
    ap.add_argument('--n-z', type=int, nargs='+', default=[100])
    ap.add_argument('--n-z-pk', type=int, default=250)
    ap.add_argument('--z-max', type=float, default=3.0)
    ap.add_argument('--repeat', type=int, default=5)
    ap.add_argument('--breakdown', action='store_true')
    ap.add_argument('--profile', action='store_true')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    cloelib_dir = os.path.abspath(tp_paths.CLOELIB.get(args.cloelib, args.cloelib))
    tp_paths.check(cloelib_dir, tp_paths.NZ_SPV3 if args.n_bins == 13 else tp_paths.NZ_DR1)
    sys.path.insert(0, cloelib_dir)
    import cloelib
    import jax
    assert cloelib.__file__.startswith(cloelib_dir), cloelib.__file__
    import euclidlib as el
    from scipy import integrate
    from cloelib.cosmology.camb_cosmology import CAMBBackground, CAMBLinearPerturbations, CAMBNonLinearPerturbations
    from cloelib.observables.photo import ShearTracer, PositionsTracer
    from cloelib.observables.photo.shear import PBJTATTLoopComputer
    from cloelib.observables.photo.positions import PBJNonlinearBiasLoopComputer
    from cloelib.summary_statistics.angular_two_point import AngularTwoPoint

    # n(z), cut at z_max and renormalised (as in the Euclid DR3/DR1 notebooks, section 1.1)
    nz_file = tp_paths.NZ_SPV3 if args.n_bins == 13 else tp_paths.NZ_DR1
    z_all, nz_all = el.phz.redshift_distributions(str(nz_file))
    sel = z_all <= args.z_max
    native = [v[sel] / integrate.trapezoid(v[sel], z_all[sel]) for v in nz_all.values()]
    n_bins = len(native)
    assert n_bins == args.n_bins, (nz_file, n_bins)

    def background():
        return CAMBBackground(H0=70.0, Omega_cdm0=0.25, Omega_b0=0.05, w0=-1.0, wa=0.0, Omega_k0=0.0, ns=0.96,
                              As=2e-9, mnu=0.06, N_mnu=1, gamma_MG=0.545)

    AIA, CIA, EtaIA, A2IA, Eta2IA, bTA, z0IA = 1.72, 0.0134, -0.41, 0.40, 2.69, -0.83, 0.62
    she_pars = {'AIA': AIA, 'CIA': CIA, 'EtaIA': EtaIA, 'A2IA': A2IA, 'bTA': bTA, 'Eta2IA': Eta2IA, 'z0IA': z0IA,
                **{f'multiplicative_bias_{i}': 0.0 for i in range(1, n_bins + 1)},
                **{f'dz_shear_{i}': 0.0 for i in range(1, n_bins + 1)},
                **{f'width_shear_{i}': 1.0 for i in range(1, n_bins + 1)}}
    pos_pars = {**{f'magnification_bias_{i}': 0.0 for i in range(1, n_bins + 1)},
                **{f'dz_pos_{i}': 0.0 for i in range(1, n_bins + 1)},
                **{f'width_pos_{i}': 1.0 for i in range(1, n_bins + 1)}}
    if args.model == 'pt':
        for name, v in (('b1', 1.0), ('b2', 0.5), ('bs2', -0.3), ('b3nl', 0.2), ('bk2', 0.1)):
            pos_pars.update({f'{name}_photo_nl_bin{i}': v for i in range(n_bins)})
    else:   # the speedcheck's polynomial linear bias
        pos_pars.update({'b1_photo_poly0': 1.33291, 'b1_photo_poly1': -0.72414, 'b1_photo_poly2': 1.0183,
                         'b1_photo_poly3': -0.14913})

    def fresh(pert):
        # same CAMB run, but every interpolator / growth cache rebuilt on use (timed; no CAMB call)
        new = copy.copy(pert)
        for k, v in list(vars(new).items()):
            if isinstance(v, dict) and ('interp' in k or 'cache' in k):
                setattr(new, k, {})
            elif k.startswith('_cloelib') and k.endswith('cache'):
                delattr(new, k)
        return new

    out = {'model': args.model, 'cloelib': cloelib_dir, 'jax': jax.__version__, 'n_bins': n_bins,
           'n_cpu': len(os.sched_getaffinity(0)), 'from_scratch': {}, 'first_call': {}, 'grids': {},
           'breakdown': {}, 'profile': None}
    for n_z in args.n_z:
        zs = np.linspace(1e-4, args.z_max, n_z)
        dndz = np.vstack([np.interp(zs, z_all[sel], v) for v in native])
        dndz /= integrate.trapezoid(dndz, zs, axis=1)[:, None]
        z_pk = zs if n_z <= args.n_z_pk else np.linspace(1e-4, args.z_max, args.n_z_pk)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            t0 = time.time()
            nonlin = CAMBNonLinearPerturbations(background(), None, z_pk, nonlinear_model='mead2020')
            lin = CAMBLinearPerturbations(background(), z_pk)
            t_camb = time.time() - t0
        out['grids'][n_z] = {'limber_nz': len(zs), 'pk_z': len(z_pk), 'k': len(nonlin.k), 'camb_s': t_camb}

        def evaluate(ells, stages=None):
            t = time.perf_counter()
            nl, li = fresh(nonlin), fresh(lin)
            if args.model == 'pt':
                pos = PositionsTracer(perturbations=nl, dndz=dndz, z=zs, galaxy_bias_model='nonlinear',
                                      nuisance_params=pos_pars, nl_bias_loop_computer=PBJNonlinearBiasLoopComputer(li))
                she = ShearTracer(perturbations=nl, dndz=dndz, z=zs, nuisance_params=she_pars, ia_model='TATT',
                                  tatt_loop_computer=PBJTATTLoopComputer(li))
            else:
                pos = PositionsTracer(perturbations=nl, dndz=dndz, z=zs, galaxy_bias_model='poly',
                                      nuisance_params=pos_pars)
                she = ShearTracer(perturbations=nl, dndz=dndz, z=zs, nuisance_params=she_pars, ia_model='NLA')
            if stages is not None:
                stages['tracers'].append(time.perf_counter() - t)
            cells = {}
            for name, (t1, t2) in (('get_Cl GG', (pos, pos)), ('get_Cl GE', (pos, she)), ('get_Cl EE', (she, she))):
                t = time.perf_counter()
                part = AngularTwoPoint(t1, t2).get_Cl(ells, 0, nl.k)
                if stages is not None:   # materialise before stopping the clock (JAX dispatch is asynchronous)
                    jax.block_until_ready([v.array if hasattr(v, 'array') else v for v in part.values()])
                    stages[name].append(time.perf_counter() - t)
                cells.update(part)
            jax.block_until_ready([np.asarray(v.array) if hasattr(v, 'array') else v for v in cells.values()])
            return cells

        for nell in args.nell:
            ells = np.geomspace(2, 2999, nell)
            jax.clear_caches()
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                t0 = time.perf_counter()
                cells = evaluate(ells)
                first = time.perf_counter() - t0
                med = float(np.median(timeit.repeat(lambda: evaluate(ells), repeat=args.repeat, number=1)))
                if args.breakdown:
                    stages = {k: [] for k in ('tracers', 'get_Cl GG', 'get_Cl GE', 'get_Cl EE')}
                    for _ in range(args.repeat):
                        evaluate(ells, stages)
                    out['breakdown'].setdefault(n_z, {})[nell] = {k: float(np.median(v)) for k, v in stages.items()}
                if args.profile and out['profile'] is None:
                    prof = cProfile.Profile()
                    prof.enable()
                    evaluate(ells)
                    prof.disable()
                    st = pstats.Stats(prof)
                    groups, n_dispatch = profile_groups(st)
                    out['profile'] = {'n_z': n_z, 'nell': nell, 'total_s': st.total_tt, 'groups_s': groups,
                                      'eager_jax_dispatches': n_dispatch}
            n_expected = n_bins * (n_bins + 1) + n_bins**2
            assert len(cells) == n_expected, (len(cells), n_expected)
            out['first_call'].setdefault(n_z, {})[nell] = first
            out['from_scratch'].setdefault(n_z, {})[nell] = med
            print(f'cloelib {args.model:6s} {n_bins} bins N_Z={n_z:5d} (P(k,z) {len(z_pk)}) n_ell={nell:5d} | '
                  f'from scratch {med:7.3f} s | first call {first:6.2f} s | {len(cells)} spectra', flush=True)
    if out['profile']:
        p = out['profile']
        print(f'profile (N_Z={p["n_z"]}, n_ell={p["nell"]}, {p["total_s"]:.3f} s): '
              + ', '.join(f'{k} {v:.3f}s' for k, v in sorted(p['groups_s'].items(), key=lambda x: -x[1]))
              + f' | {p["eager_jax_dispatches"]} eager JAX dispatches')
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1)


if __name__ == '__main__':
    main()
