"""Re-run the E1 tracer-grid sweep (n_p = 255, Simpson) against a given cloelib checkout and compare
with the unfixed 384 results (results_384_<model>.npz). Usage:
    CLOELIB_SRC=/path/to/cloelib python verify_fix.py --model nlbias_NLA"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zconv_common as zc  # noqa: E402

NT = [100, 101, 150, 151, 200, 201, 250, 251, 3201]
ap = argparse.ArgumentParser()
ap.add_argument('--model', required=True)
model = ap.parse_args().model
new = {}
for n_t in NT:
    new[n_t] = zc.check_spectra(model, n_t, 255)
    zc._clear_jit_caches()
np.savez(Path(__file__).resolve().parents[1] / 'results' / f'results_{zc.CLOELIB_SRC}_{model}_verify.npz',
         **{f'nt={n}|{k}': v for n, d in new.items() for k, v in d.items()})
_here = Path(__file__).resolve().parents[1] / 'results'
old = np.load(_here / f'results_384_{model}.npz' if (_here / f'results_384_{model}.npz').exists()
              else _here / f'results_main_{model}.npz')   # unfixed: 384 worktree, or main for linear models
m = zc.ELLS > 20
ref_old = {k: old[f'E1|{model}|simpson|nt=3201|np=255|{k}'] for k in zc.CHECK_KEYS}
nos = None
print(f'{model}: max |C/C_ref - 1| [%] (each version vs its own n_t = 3201), before -> after the fix')
print(f'{"n_t":>5s} ' + ' '.join(f'{k:>17s}' for k in zc.CHECK_KEYS))
for n in NT[:-1]:
    row = []
    for k in zc.CHECK_KEYS:
        b = 100 * np.max(np.abs(old[f'E1|{model}|simpson|nt={n}|np=255|{k}'][m] / ref_old[k][m] - 1))
        a = 100 * np.max(np.abs(new[n][k][m] / new[3201][k][m] - 1))
        row.append(f'{b:7.3f} -> {a:6.3f}')
    print(f'{n:5d} ' + ' '.join(f'{r:>17s}' for r in row))
print('converged result, after vs before the fix [%]:',
      {k: round(100 * np.max(np.abs(new[3201][k][m] / ref_old[k][m] - 1)), 4) for k in zc.CHECK_KEYS})
