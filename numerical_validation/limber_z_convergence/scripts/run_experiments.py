"""Run the redshift-convergence experiments and save every check spectrum.

    CLOELIB_SRC=main python run_experiments.py --model linear_NLA     # main: linear_NLA, linear_TATT
    CLOELIB_SRC=384  python run_experiments.py --model nlbias_TATT    # 384: + nlbias_NLA, nlbias_TATT

One model per process: every grid size is a new JAX compilation, and one process compiling a whole
sweep exhausts the kernel's memory-mapping limit (vm.max_map_count = 65530 here; LLVM then fails with
"Cannot allocate memory"). JAX's caches are also cleared after every spectrum.

Output: results_<CLOELIB_SRC>_<model>.npz with one entry per (experiment, setting, n_t, n_p, spectrum),
keyed 'E1|<model>|<quadrature>|nt=<n_t>|np=<n_p>|<spectrum>' etc., plus 'ells'.

E1  tracer grid n_t varied (odd and even), P(k,z) grid fixed at n_p = 255, Simpson vs trapezoid weights
    -> convergence of the Limber + window-function quadrature alone.
E2  P(k,z) grid n_p varied, tracer grid fixed at n_t = E2_NT -> convergence in the P(k,z) redshift sampling.
E3  as E2, but signed effective spectra (TATT, non-linear bias) interpolated in P instead of log|P|.
E0  the benchmark's coupled set-up, n_t = n_p = N (as in time_comparison_Euclid_DR3.ipynb).
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zconv_common as zc  # noqa: E402

E1_NT = [100, 101, 150, 151, 200, 201, 250, 251, 400, 401, 800, 801, 1600, 1601, 3200, 3201]
E1_NP = 255
E2_NT = 1601
E2_NP = [50, 51, 100, 101, 150, 151, 200, 201, 254, 255]
E0_N = [100, 101, 150, 151, 200, 201, 250, 251, 255]

ap = argparse.ArgumentParser()
ap.add_argument('--model', required=True, choices=list(zc.MODELS))
models = [ap.parse_args().model]
OUT = Path(__file__).resolve().parents[1] / 'results' / f'results_{zc.CLOELIB_SRC}_{models[0]}.npz'
out = {'ells': zc.ELLS}
t_start = time.time()


def run(tag, model, setting, n_t, n_p):
    t0 = time.time()
    sp = zc.check_spectra(model, n_t, n_p)
    for k, v in sp.items():
        out[f'{tag}|{model}|{setting}|nt={n_t}|np={n_p}|{k}'] = v
    zc._clear_jit_caches()   # free this grid's compiled executables (memory-mapping limit)
    print(f'[{time.time() - t_start:6.0f}s] {tag} {model:12s} {setting:9s} n_t={n_t:5d} n_p={n_p:4d} '
          f'({time.time() - t0:5.1f}s)', flush=True)


for model in models:
    for quad in ('simpson', 'trapezoid'):
        zc.set_quadrature(quad)
        for n_t in E1_NT:
            run('E1', model, quad, n_t, E1_NP)
    zc.set_quadrature('simpson')
    for n_p in E2_NP:
        run('E2', model, 'logabs', E2_NT, n_p)
    if 'TATT' in model or 'nlbias' in model:
        zc.set_signed_interp('linear_p')
        for n_p in E2_NP:
            run('E3', model, 'linear_p', E2_NT, n_p)
        zc.set_signed_interp('logabs')
    for n in E0_N:
        run('E0', model, 'coupled', n, n)
    np.savez(OUT, **out)   # save as we go

w, sums, exact = zc.stacked_weights_report(6)
out['stacked_simpson_6'] = w
np.savez(OUT, **out)
print('done', len(out) - 2, 'spectra')
