"""Re-run the former-CLOE photometric 3x2pt timing of the July 2026 speedcheck notebook.

The speedcheck runs `run_cloe.py configs/config_default_speedtest_3x2pt_linear_standardized_fixedparams.yaml`
once per process (cobaya `evaluate` sampler, `timing: true`) with its "standardized" photo.py
(window tables z_wsamp 1000 -> 100, Limber step 0.01 -> 0.04), and reads cobaya's
"Average evaluation time for Euclid" (one evaluation). This script builds exactly that model in-process:
  * their photo_standardized.py replaces cloe.photometric_survey.photo before CLOE is imported;
  * the cobaya info dict is produced by CLOE's own LikelihoodUI from their YAML, as run_cloe.py does;
  * the first logposterior call runs CAMB (not timed) and cobaya's own timer on the Euclid component gives
    their metric for that evaluation;
  * then EuclidLikelihood.logp is called --repeat more times directly (cobaya would return its cached result
    for an unchanged point), and the median of each step is recorded, as cloe_former_benchmark.py does.
--ia-flag / --nl-bias switch CLOE to TATT and to the one-loop photometric bias on the same data, to show how
much of CLOE's time depends on the model.

Run with the cloe-former python (tp_paths.PY_CLOE_FORMER):
    python cloe_speedcheck.py --out out.json
Their CLOE configs must be in tp_paths.CLOE / 'configs' (environment/setup_external.sh copies them from
tp_paths.SPEEDCHECK / 'their_files/cloefiles/configs').
"""
import argparse
import importlib.util
import json
import os
import sys
import time
import timeit
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))   # time_profiling/, for tp_paths
import tp_paths  # noqa: E402

CLOE_DIR = str(tp_paths.CLOE)
CONFIG = 'configs/config_default_speedtest_3x2pt_linear_standardized_fixedparams.yaml'
STANDARDIZED_PHOTO = str(tp_paths.SPEEDCHECK / 'their_files' / 'cloefiles' / 'cloe' / 'photometric_survey'
                         / 'photo_standardized.py')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repeat', type=int, default=20)       # N_REPEAT_CLOE in the speedcheck
    ap.add_argument('--ia-flag', type=int, default=None, help='override IA_flag (0 NLA, 1 TATT)')
    ap.add_argument('--nl-bias', type=int, default=None, help='override NL_flag_phot_bias (1 = one-loop FAST-PT)')
    ap.add_argument('--k-samp', type=int, default=None,
                    help='override k_samp (FAST-PT needs an even number; their config has 209)')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    tp_paths.check(CLOE_DIR, os.path.join(CLOE_DIR, CONFIG), STANDARDIZED_PHOTO)
    os.chdir(CLOE_DIR)
    sys.path.insert(0, CLOE_DIR)

    # their standardized photo.py in place of CLOE's (same file otherwise: see the diff in the notebook).
    # CLOE is imported first (its package __init__ imports photo), then every reference to the original
    # Photo class in the loaded cloe modules is pointed at theirs.
    import cloe.photometric_survey.photo as orig_photo
    spec = importlib.util.spec_from_file_location('cloe_photo_standardized', STANDARDIZED_PHOTO)
    photo_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(photo_mod)
    import cloe.cobaya_interface   # noqa: F401  (load the modules that hold Photo)
    import cloe.like_calc.euclike   # noqa: F401  (imported lazily otherwise; it builds the Photo instance)
    orig_cls, n_swapped = orig_photo.Photo, 0
    for name, mod in list(sys.modules.items()):
        if name.startswith('cloe') and getattr(mod, 'Photo', None) is orig_cls:
            mod.Photo = photo_mod.Photo
            n_swapped += 1
    assert n_swapped, 'Photo class not found in any cloe module'

    from cobaya.model import get_model
    from cloe.user_interface.likelihood_ui import LikelihoodUI
    import cloe.auxiliary.likelihood_yaml_handler as lyh

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        ui = LikelihoodUI(user_config_file=CONFIG, user_dict={})
        info = ui._config['Cobaya']                       # what LikelihoodUI._run_cobaya passes to cobaya.run
        ui._check_and_update_likelihood_fields(info['likelihood']['Euclid'])
        ui._check_and_update_params_field(info)
        lyh.update_cobaya_dict_with_halofit_version(info)
        euclid_info = info['likelihood']['Euclid']
        if args.ia_flag is not None:
            euclid_info['IA_flag'] = args.ia_flag
        if args.nl_bias is not None:
            euclid_info['NL_flag_phot_bias'] = args.nl_bias
        if args.k_samp is not None:
            euclid_info['k_samp'] = args.k_samp
        info['timing'] = True
        info.pop('sampler', None)
        info.pop('output', None)
        t0 = time.time()
        model = get_model(info)
        t_init = time.time() - t0
        euclid = model.likelihood['Euclid']
        assert type(euclid.likefinal.phot_ins) is photo_mod.Photo, 'standardized Photo not in use'
        assert euclid.likefinal.phot_ins.z_wsamp == 100, 'standardized photo.py not in use'

        captured = {}
        orig_logp = euclid.logp

        def recording_logp(**kw):
            captured.update(kw)
            return orig_logp(**kw)
        euclid.logp = recording_logp
        t0 = time.time()
        logpost = model.logposterior({})
        t_first = time.time() - t0
        euclid.logp = orig_logp
    cobaya_euclid = euclid.timer.get_time_avg() if euclid.timer else None
    cobaya_camb = {name: th.timer.get_time_avg() for name, th in model.theory.items() if th.timer}

    like, cosmo = euclid.likefinal, euclid.cosmo
    z_win = cosmo.cosmo_dic['z_win']
    steps = {'passing_requirements': lambda: euclid.passing_requirements(None, None, **captured),
             'update_cosmo_dic': lambda: cosmo.update_cosmo_dic(z_win, 0.05),
             'loglike (C_ell + chi2)': lambda: like.loglike(cosmo.cosmo_dic, 0)}   # npar = 0: no sampled params
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        full = timeit.repeat(lambda: euclid.logp(**captured), repeat=args.repeat, number=1)
        step_t = {}
        for name, fn in steps.items():
            try:
                step_t[name] = float(np.median(timeit.repeat(fn, repeat=args.repeat, number=1)))
            except Exception as exc:   # signature differs between CLOE versions: report, do not fail
                step_t[name] = f'not timed: {exc!r}'[:200]

    out = {'config': CONFIG, 'IA_flag': euclid_info['IA_flag'], 'NL_flag_phot_bias': euclid_info['NL_flag_phot_bias'],
           'k_samp': euclid_info['k_samp'],
           'n_cpu': len(os.sched_getaffinity(0)), 'init_s': t_init, 'first_logposterior_incl_camb_s': t_first,
           'cobaya_euclid_one_evaluation_s': cobaya_euclid, 'cobaya_theory_s': cobaya_camb,
           'logp_median_s': float(np.median(full)), 'logp_all_s': full, 'steps_median_s': step_t,
           'chi2': float(-2 * logpost.loglikes[0]), 'z_grid_for_cl': len(like.phot_ins.z_grid_for_cl),
           'z_wsamp': like.phot_ins.z_wsamp}
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1)
    print(f'CLOE IA_flag={out["IA_flag"]} NL_flag_phot_bias={out["NL_flag_phot_bias"]} | cobaya Euclid timer, one '
          f'evaluation: {cobaya_euclid:.4f} s | logp median of {args.repeat}: {out["logp_median_s"]:.4f} s | steps: '
          + ', '.join(f'{k} {v:.4f}s' if isinstance(v, float) else f'{k} {v}' for k, v in step_t.items())
          + f' | chi2 {out["chi2"]:.6e} | camb (excluded) {cobaya_camb}')


if __name__ == '__main__':
    main()
