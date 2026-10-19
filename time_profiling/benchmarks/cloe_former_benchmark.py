"""Former CLOE (github.com/cloe-org/cloe) timing: one full photometric 3x2pt evaluation from scratch.

Used by the notebooks in studies/ (euclid_dr3, euclid_dr1).
Default model: TATT (IA_flag = 1) + one-loop photometric galaxy bias (NL_flag_phot_bias = 1), Mead2020
(NL_flag_phot_matter = 3); --model linear switches to NLA + linear bias. 13 SPV3 bins by default (--n-bins for
another n(z) file). Run with the cloe-former python (tp_paths.PY_CLOE_FORMER); the CLOE checkout is
tp_paths.CLOE:

    python cloe_former_benchmark.py --nell 32 100 --repeat 3 --n-z 100 --nz-file nzTabSPV3_zs.dat --out out.json

Timing protocol (same as the notebook): one full 3x2pt evaluation from scratch, CAMB excluded.
  * one model.logposterior call first runs CAMB through cobaya (not timed) and records the parameter
    dict cobaya passes to the likelihood;
  * timed: EuclidLikelihood.logp(**params) = passing_requirements (reads CAMB's products from cobaya)
    + Cosmology.update_cosmo_dic (interpolators, FAST-PT TATT and EFT bias loops)
    + Euclike.create_photo_theory (C_ell); the chi^2 is replaced by a no-op;
  * the first call at each ell-grid and the median of --repeat further calls are both recorded,
    plus the median of each of the three parts.
The ell grid is patched to np.geomspace(2, 2999, n_ell) on all three probes, and the Limber
prefactors are recomputed (photo.set_prefactor), as in CLOE-NL/time_cloe_1000ells.py.

Redshift sampling, matched to the notebook's common grid (--n-z points, --z-max):
  * n(z): --nz-file, tabulated on the notebook's zs = linspace(1e-4, z_max, n_z);
  * P(k, z) / PT interpolators: z_samp = n_z (or min(n_z, --n-z-pk): CAMB takes at most 256 redshifts) on
    z_min = 0, z_max (CLOE's z_win);
  * Limber integral: Photo.z_grid_for_cl (hard-coded arange(0.001, 4, 0.01) = 400 points) -> zs;
  * window-function tables: Photo.z_winterp / z_wsamp (hard-coded 1000 log-spaced points) -> zs.
"""
import argparse
import json
import os
import sys
import time
import timeit
import types
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..')))   # time_profiling/, for tp_paths
import tp_paths  # noqa: E402

CLOE_DIR = str(tp_paths.CLOE)
sys.path.insert(0, CLOE_DIR)

from cobaya.model import get_model                      # noqa: E402
from cloe.cobaya_interface import EuclidLikelihood       # noqa: E402

N_BINS = 13              # --n-bins overrides (the n(z) file must have that many columns)
SAMPLE = 'SPV3_13bins'   # cloe/data/<sample>: built by make_sample() from CLOE's own data/ExternalBenchmark

# Same cosmology / nuisance values as the notebook (section 1.2)
H0, OMC, OMB, NS, AS, MNU = 70.0, 0.25, 0.05, 0.96, 2e-9, 0.06
h = H0 / 100
AIA, EtaIA, A2IA, Eta2IA, bTA, z0IA = 1.72, -0.41, 0.40, 2.69, -0.83, 0.62
B1, B2 = 1.0, 0.5
# CLOE's non-linear photometric bias uses the Lagrangian (b1, b2, bG2, bG3) basis. Timing does
# not depend on the values; these are illustrative non-zero values of the same size.
BG2, BG3 = -0.3, 0.2

ells_range = [[2, 3000]]
# Photometric bin mean redshifts of the 13 SPV3 bins; for another --n-bins they are computed from --nz-file
REDSHIFTS_13 = [0.27575, 0.37635, 0.44634, 0.54284, 0.62145, 0.70957, 0.7986,
                0.86687, 0.97753, 1.09136, 1.24264, 1.47918, 1.89264]
CHECKS_13 = [('GG', 0, 0), ('GG', 6, 6), ('GE', 2, 10), ('EE', 0, 0), ('EE', 6, 12), ('EE', 12, 12)]


def _aps(pairs):
    return {'statistics': 'angular_power_spectrum',
            'angular_power_spectrum': {'bins': {f'n{i}': {f'n{j}': {'ell_range': ells_range} for j in js}
                                                for i, js in pairs}}}


def _specs(n_bins):
    auto = [(i, range(i, n_bins + 1)) for i in range(1, n_bins + 1)]
    cross = [(i, range(1, n_bins + 1)) for i in range(1, n_bins + 1)]
    return {'GCphot': _aps(auto), 'WL': _aps(auto), 'WL-GCphot': _aps(cross)}   # WL-GCphot: n{WL}-n{GC}


def _bin_params(n_bins):
    return {
        **{f'b1_photo_bin{i}': B1 for i in range(1, n_bins + 1)},
        **{f'b2_photo_bin{i}': B2 for i in range(1, n_bins + 1)},
        **{f'bG2_photo_bin{i}': BG2 for i in range(1, n_bins + 1)},
        **{f'bG3_photo_bin{i}': BG3 for i in range(1, n_bins + 1)},
        **{f'magnification_bias_{i}': 0.0 for i in range(1, n_bins + 1)},
        **{f'multiplicative_bias_{i}': 0.0 for i in range(1, n_bins + 1)},
        **{f'dz_{i}_GCphot': 0.0 for i in range(1, n_bins + 1)},
        **{f'dz_{i}_WL': 0.0 for i in range(1, n_bins + 1)},
    }


params = {
    'H0': H0, 'ombh2': OMB * h**2, 'omch2': OMC * h**2, 'ns': NS, 'As': AS, 'mnu': MNU,
    'nnu': 3.046, 'tau': 0.0544, 'omk': 0.0, 'w': -1.0, 'wa': 0.0,
    'a1_ia': AIA, 'eta1_ia': EtaIA, 'a2_ia': A2IA, 'eta2_ia': Eta2IA, 'b1_ia': bTA,
    'beta1_ia': 0.0, 'pivot_redshift': z0IA,
    **_bin_params(N_BINS),
}

info = {
    'debug': False,
    'likelihood': {'Euclid': {
        'external': EuclidLikelihood,
        'aliases': ['euclid'],
        'speed': 500,
        'solver': 'camb',
        'k_max_extrap': 500.0, 'k_min_extrap': 1e-05, 'k_samp': 1000,
        'z_min': 0.0, 'z_max': 3.0, 'z_samp': 100,         # set from --n-z / --z-max in main()
        'NL_flag_phot_matter': 3,          # Mead2020
        'NL_flag_phot_baryon': 0,
        'NL_flag_phot_bias': 1,            # non-linear photometric galaxy bias
        'NL_flag_spectro': 0,
        'IA_flag': 1,                      # TATT
        'bias_model': 1,
        'magbias_model': 2,
        'use_magnification_bias_spectro': False,
        'use_gamma_MG': False,
        'f_out_z_dep': False,
        'plot_observables_selection': False,
        'data': {
            'sample': SAMPLE,
            'photo': {
                'redshifts': REDSHIFTS_13,         # set from --nz-file in main() if --n-bins != 13
                'luminosity_ratio': 'luminosity_ratio.dat',
                'IA_model': 'zNLA',
                'cov_3x2pt': 'CovMat-3x2pt-{:s}-32Bins-13245deg2.npy',
                'cov_GC': 'CovMat-PosPos-{:s}-32Bins-13245deg2.npy',
                'cov_WL': 'CovMat-ShearShear-{:s}-32Bins-13245deg2.npy',
                'cov_model': 'GaussSSC',
                'cov_is_num': False,
                'cov_nsim': 10000,
                'ndens_GC': 'nzTabSPV3.dat',
                'ndens_WL': 'nzTabSPV3.dat',
                'root_GC': 'Cls_{:s}_PosPos_C00.dat',
                'root_WL': 'Cls_{:s}_ShearShear_C00.dat',
                'root_XC': 'Cls_{:s}_PosShear_C00.dat',
                # only loaded at init: matrix_transform_phot = False and no pseudo-Cl, so it is never
                # applied. No 13-bin file exists; the 10-bin one from the repo is linked here.
                'root_mixing_matrix': 'fs2_mms_10zbins_32ellbins.fits',
                'photo_data': 'standard',
                'Fourier': True,
            },
            'spectro': {
                'redshifts': ['1.', '1.2', '1.4', '1.65'],
                'edges': [0.9, 1.1, 1.3, 1.5, 1.8],
                'root': 'cov_power_galaxies_EFT_benchmark_z{:s}.fits',
                'cov_is_num': False,
                'cov_nsim': 3500,
                'Fourier': True,
            },
        },
        'observables_selection': {
            'WL': {'WL': True, 'GCphot': True, 'GCspectro': False},
            'GCphot': {'GCphot': True, 'GCspectro': False},
            'GCspectro': {'GCspectro': False},
            'CG': {'CG': False},
            'add_phot_RSD': False,
            'matrix_transform_phot': False,
        },
        'observables_specifications': _specs(N_BINS),
    }},
    'params': params,
    'theory': {'camb': {'extra_args': {'num_nu_massive': 1, 'dark_energy_model': 'ppf'},
                        'stop_at_error': True}},
}


def sample_ready(sample):
    photo = info['likelihood']['Euclid']['data']['photo']
    d = os.path.join(CLOE_DIR, 'data', sample, 'Photometric', 'data')
    return all(os.path.exists(os.path.join(d, photo[k].format(photo['IA_model']))) for k in ('root_GC', 'root_XC', 'root_WL'))


def make_sample(sample, n_bins, n_ell_data=32):
    """CLOE's data/<sample> for an n_bins analysis, built from its own data/ExternalBenchmark (idempotent).

    CLOE's reader builds the masked data vector and loads the 3x2pt covariance at init, so their shapes must
    match n_bins even though the chi^2 is never computed here (theory_only below). The data vectors are
    placeholders (ones, on n_ell_data log-spaced ells) and the covariance is an identity matrix: neither enters
    the timed theory evaluation. The spectroscopic files, luminosity ratio and (unused) mixing matrix are linked
    to ExternalBenchmark. The n(z) file is written by the caller (the notebooks) into <sample>/Photometric.

    Note: the Euclid DR3 notebooks of October 2026 ran with an SPV3_13bins sample whose data vectors and
    covariance came from the CLOE-NL repository. Only CLOE's initialisation reads them, so the timings do not
    depend on them.
    """
    src, dst = os.path.join(CLOE_DIR, 'data', 'ExternalBenchmark'), os.path.join(CLOE_DIR, 'data', sample)
    os.makedirs(os.path.join(dst, 'Photometric', 'data'), exist_ok=True)
    for name in ('matteo_bias.npy', 'Pk_z0.0_ISTF.dat', 'Pm_z0.0_ISTF.dat', 'Spectroscopic'):
        if not os.path.lexists(os.path.join(dst, name)):
            os.symlink(os.path.join(src, name), os.path.join(dst, name))
    if not os.path.lexists(os.path.join(dst, 'Photometric', 'luminosity_ratio.dat')):
        os.symlink(os.path.join(src, 'Photometric', 'luminosity_ratio.dat'),
                   os.path.join(dst, 'Photometric', 'luminosity_ratio.dat'))
    d_src, d_dst = os.path.join(src, 'Photometric', 'data'), os.path.join(dst, 'Photometric', 'data')
    photo = info['likelihood']['Euclid']['data']['photo']
    if not os.path.lexists(os.path.join(d_dst, photo['root_mixing_matrix'])):
        os.symlink(os.path.join(d_src, photo['root_mixing_matrix']), os.path.join(d_dst, photo['root_mixing_matrix']))
    ells = np.geomspace(10.0, 2999.0, n_ell_data)
    pairs = {'root_GC': [f'P{i}-P{j}' for i in range(1, n_bins + 1) for j in range(i, n_bins + 1)],
             'root_XC': [f'P{i}-E{j}' for i in range(1, n_bins + 1) for j in range(1, n_bins + 1)],
             'root_WL': [f'E{i}-E{j}' for i in range(1, n_bins + 1) for j in range(i, n_bins + 1)]}
    n_dv = 0
    for key, cols in pairs.items():
        np.savetxt(os.path.join(d_dst, photo[key].format(photo['IA_model'])),
                   np.column_stack([ells, np.ones((n_ell_data, len(cols)))]), delimiter='\t',
                   header='\t'.join(['ells', *cols]))
        n_dv += n_ell_data * len(cols)
    cov = os.path.join(d_dst, photo['cov_3x2pt'].format(photo['cov_model']))
    if not os.path.exists(cov) or np.load(cov, mmap_mode='r').shape != (n_dv, n_dv):
        np.save(cov, np.eye(n_dv))


def first_and_median(fn, repeat):
    """Time of the first call, and median of `repeat` further calls."""
    t0 = time.perf_counter()
    fn()
    first = time.perf_counter() - t0
    return first, float(np.median(timeit.repeat(fn, repeat=repeat, number=1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nell', type=int, nargs='+', default=[32, 100, 500, 1000, 3000])
    ap.add_argument('--repeat', type=int, default=3)
    ap.add_argument('--out', required=True)
    ap.add_argument('--spectra-out', default=None, help='npz with a few n_ell=32 spectra for a sanity check')
    ap.add_argument('--n-z', type=int, default=100, help='common number of redshift points')
    ap.add_argument('--z-max', type=float, default=3.0)
    ap.add_argument('--nz-file', default='nzTabSPV3_zs.dat', help='n(z) file in data/<sample>/Photometric')
    ap.add_argument('--n-bins', type=int, default=N_BINS, help='number of tomographic bins in --nz-file')
    ap.add_argument('--n-z-pk', type=int, default=None,
                    help='cap on the P(k, z) / PT grid z_samp (CAMB takes at most 256 redshifts); the Limber and '
                         'window grids keep --n-z points')
    ap.add_argument('--model', choices=('pt', 'linear'), default='pt',
                    help='pt: TATT + one-loop bias (default); linear: NLA + linear bias, as in the July 2026 speedcheck')
    ap.add_argument('--sample', default=SAMPLE,
                    help='CLOE data/<sample>; built by make_sample() if it has no data vectors yet')
    ap.add_argument('--checks', default=None,
                    help='sanity-check spectra for --spectra-out, "GG:0:0,GE:2:10,..." (0-based bins); '
                         'default: the 13-bin list')
    args = ap.parse_args()
    checks = CHECKS_13 if args.checks is None else [
        (p, int(i), int(j)) for p, i, j in (c.split(':') for c in args.checks.split(','))]

    if not sample_ready(args.sample):
        make_sample(args.sample, args.n_bins)
    info['likelihood']['Euclid']['data']['sample'] = args.sample
    nz_tab = np.loadtxt(os.path.join(CLOE_DIR, 'data', args.sample, 'Photometric', args.nz_file))
    assert nz_tab.shape[1] == args.n_bins + 1, f'{args.nz_file}: {nz_tab.shape[1] - 1} bins, --n-bins {args.n_bins}'
    if args.n_bins != 13:
        z_tab = nz_tab[:, 0]
        means = [float(np.trapz(z_tab * n, z_tab) / np.trapz(n, z_tab)) for n in nz_tab[:, 1:].T]
        info['likelihood']['Euclid']['data']['photo']['redshifts'] = means
        info['likelihood']['Euclid']['observables_specifications'] = _specs(args.n_bins)
        for k in _bin_params(N_BINS):      # params is info['params']: replace the per-bin entries in place
            del params[k]
        params.update(_bin_params(args.n_bins))

    zs = np.linspace(1e-4, args.z_max, args.n_z)
    euclid_info = info['likelihood']['Euclid']
    euclid_info.update(z_min=0.0, z_max=args.z_max,
                       z_samp=args.n_z if args.n_z_pk is None else min(args.n_z, args.n_z_pk))
    if args.model == 'linear':
        euclid_info.update(IA_flag=0, NL_flag_phot_bias=0)
    euclid_info['data']['photo'].update(ndens_GC=args.nz_file, ndens_WL=args.nz_file)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        t0 = time.time()
        model = get_model(info)
        t_init = time.time() - t0
        euclid = model.likelihood['Euclid']
        like = euclid.likefinal
        phot = like.phot_ins
        phot.z_grid_for_cl = zs.copy()                      # Limber integral
        phot.z_winterp, phot.z_wsamp = zs.copy(), len(zs)   # window-function tables

        # Record the exact parameter dict cobaya passes to the likelihood, during the one call that
        # also runs CAMB (not timed). Later logp calls reuse cobaya's stored CAMB products.
        captured = {}
        orig_logp = euclid.logp

        def recording_logp(**params_values):
            captured.update(params_values)
            return orig_logp(**params_values)

        euclid.logp = recording_logp
        t0 = time.time()
        model.logposterior({})
        t_camb_call = time.time() - t0
        euclid.logp = orig_logp

    # The C_ell computation only: the chi^2 against data/covariance is replaced by a no-op
    def theory_only(self, dictionary, npar=None):
        self._last_theory = self.create_photo_theory(dictionary)
        return 0.0

    like.loglike = types.MethodType(theory_only, like)
    cosmo = euclid.cosmo
    z_win = cosmo.cosmo_dic['z_win']
    print(f'CLOE model init {t_init:.1f} s | first logposterior (incl. CAMB) {t_camb_call:.1f} s', flush=True)

    out = {'from_scratch': {}, 'first_call': {}, 'parts': {}, 'n_spectra': {},
           'init_s': t_init, 'first_logposterior_incl_camb_s': t_camb_call,
           'n_k': int(len(cosmo.cosmo_dic['k_win'])) if 'k_win' in cosmo.cosmo_dic else None,
           'n_z': int(len(z_win)), 'z_win_range': [float(z_win[0]), float(z_win[-1])],
           'n_z_limber': int(len(phot.z_grid_for_cl)), 'n_z_windows': int(phot.z_wsamp),
           'n_z_nz_file': int(len(nz_tab)), 'n_bins': args.n_bins, 'model': args.model}

    def full():   # one evaluation from scratch (CAMB excluded)
        return euclid.logp(**captured)

    parts = {'passing_requirements': lambda: euclid.passing_requirements(None, None, **captured),
             'update_cosmo_dic': lambda: cosmo.update_cosmo_dic(z_win, 0.05),
             'create_photo_theory': lambda: like.create_photo_theory(cosmo.cosmo_dic)}

    for nell in args.nell:
        ells = np.geomspace(2, 2999, nell)
        like.scales_WL = ells
        like.scales_XC = ells
        like.scales_GC_phot = ells
        like.phot_ins.set_prefactor(ells_WL=ells, ells_XC=ells, ells_GC_phot=ells)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            out['first_call'][nell], out['from_scratch'][nell] = first_and_median(full, args.repeat)
            out['n_spectra'][nell] = int(np.size(like._last_theory) // nell)
            out['parts'][nell] = {name: first_and_median(fn, args.repeat)[1] for name, fn in parts.items()}
        print(f'n_ell={nell:5d} | CLOE from scratch {out["from_scratch"][nell]:7.3f}s  first call '
              f'{out["first_call"][nell]:7.3f}s  (' + ', '.join(f'{k} {v:.3f}s' for k, v in out['parts'][nell].items())
              + f') {out["n_spectra"][nell]} spectra', flush=True)

    if args.spectra_out:
        ells = np.geomspace(2, 2999, 32)
        like.phot_ins.set_prefactor(ells_WL=ells, ells_XC=ells, ells_GC_phot=ells)
        like.phot_ins.update(cosmo.cosmo_dic)
        sp = {'ell': ells}
        for probe, i, j in checks:
            fn = {'GG': like.phot_ins.Cl_GC_phot, 'GE': like.phot_ins.Cl_cross, 'EE': like.phot_ins.Cl_WL}[probe]
            # Cl_cross(ells, bin_i, bin_j): bin_i = WL (source), bin_j = GCphot (lens)
            a, b = (j + 1, i + 1) if probe == 'GE' else (i + 1, j + 1)
            sp[f'{probe}_{i}_{j}'] = np.asarray(fn(ells, a, b))
        np.savez(args.spectra_out, **sp)

    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1)
    print('written', args.out)


if __name__ == '__main__':
    main()
