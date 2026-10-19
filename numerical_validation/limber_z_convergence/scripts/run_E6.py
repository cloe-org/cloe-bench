"""E6: GG convergence on the tracer grid with cloelib's sigma^4 subtraction switched off (nlbias_NLA, n_p = 255).
CLOELIB_SRC=384 python run_E6.py -> results_384_nlbias_NLA_E6.npz, keys 'E6|<variant>|nt=<n_t>|<spectrum>'."""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zconv_common as zc  # noqa: E402

NT = [100, 101, 150, 151, 200, 250, 400, 800, 3201]
BASE = dict(zc.NUIS_POS_NL)
VARIANTS = {'sigma4 subtracted (cloelib)': (True, {}),
            'no sigma4': (False, {}),
            'no sigma4, bk2 = 0': (False, {'bk2_photo_nl_bin': 0.0})}
out = {'ells': zc.ELLS}
t0 = time.time()
for name, (sub, change) in VARIANTS.items():
    zc.SUBTRACT_SIG4 = sub
    zc.NUIS_POS_NL.clear(); zc.NUIS_POS_NL.update(BASE)
    for prefix, val in change.items():
        for k in list(zc.NUIS_POS_NL):
            if k.startswith(prefix):
                zc.NUIS_POS_NL[k] = val
    for n_t in NT:
        for k, v in zc.check_spectra('nlbias_NLA', n_t, 255).items():
            out[f'E6|{name}|nt={n_t}|{k}'] = v
        zc._clear_jit_caches()
        print(f'[{time.time() - t0:5.0f}s] {name:28s} n_t={n_t}', flush=True)
np.savez(Path(__file__).resolve().parents[1] / 'results' / 'results_384_nlbias_NLA_E6.npz', **out)
m = zc.ELLS > 20
print('\nGG_1_1 error vs the same variant at n_t = 3201 [%]')
print(f'{"variant":28s} ' + ' '.join(f'{n:>7d}' for n in NT[:-1]))
for name in VARIANTS:
    ref = out[f'E6|{name}|nt=3201|GG_1_1']
    print(f'{name:28s} ' + ' '.join(f'{100 * np.max(np.abs(out[f"E6|{name}|nt={n}|GG_1_1"][m] / ref[m] - 1)):7.3f}' for n in NT[:-1]))
# how much the sigma^4 terms are of the total, at n_t = 3201
a, b = out['E6|sigma4 subtracted (cloelib)|nt=3201|GG_1_1'], out['E6|no sigma4|nt=3201|GG_1_1']
print('\nGG_1_1, n_t = 3201: C(sigma4 subtracted) / C(no sigma4) at ell =', np.round(zc.ELLS[[5, 15, 25, 31]]).astype(int),
      '->', np.round(a[[5, 15, 25, 31]] / b[[5, 15, 25, 31]], 3))
