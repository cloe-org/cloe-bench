"""E4: E1 (tracer grid varied, n_p = 255) for the non-linear-bias models with signed effective spectra
interpolated in P (akima) instead of log10|P| + sign. Run with CLOELIB_SRC=384 --model nlbias_NLA|nlbias_TATT.
Saves results_<src>_<model>_E4.npz with keys 'E4|<model>|linear_p|nt=<n_t>|np=255|<spectrum>'."""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zconv_common as zc  # noqa: E402

NT = [100, 101, 150, 151, 200, 201, 250, 251, 400, 401, 800, 801, 1601, 3201]
ap = argparse.ArgumentParser()
ap.add_argument('--model', required=True, choices=['nlbias_NLA', 'nlbias_TATT', 'linear_TATT'])
model = ap.parse_args().model
out = {'ells': zc.ELLS}
t_start = time.time()
zc.set_signed_interp('linear_p')
for n_t in NT:
    t0 = time.time()
    for k, v in zc.check_spectra(model, n_t, 255).items():
        out[f'E4|{model}|linear_p|nt={n_t}|np=255|{k}'] = v
    zc._clear_jit_caches()
    print(f'[{time.time() - t_start:6.0f}s] E4 {model} n_t={n_t} ({time.time() - t0:.1f}s)', flush=True)
np.savez(Path(__file__).resolve().parents[1] / 'results' / f'results_{zc.CLOELIB_SRC}_{model}_E4.npz', **out)
print('done')
