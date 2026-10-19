"""E5: which non-linear-bias term makes GG converge slowly on the tracer grid.
Tracer grid varied (n_p = 255) for nlbias_NLA with bias terms switched off one at a time.
CLOELIB_SRC=384 python run_E5.py  ->  results_384_nlbias_NLA_E5.npz, keys 'E5|<variant>|nt=<n_t>|<spectrum>'."""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zconv_common as zc  # noqa: E402

NT = [100, 150, 200, 250, 400, 800, 3201]
BASE = dict(zc.NUIS_POS_NL)
VARIANTS = {   # parameter prefix -> value (all bins)
    'all terms': {},
    'bk2 = 0': {'bk2_photo_nl_bin': 0.0},
    'b2 = bs2 = b3nl = 0': {'b2_photo_nl_bin': 0.0, 'bs2_photo_nl_bin': 0.0, 'b3nl_photo_nl_bin': 0.0},
    'b1 only': {'b2_photo_nl_bin': 0.0, 'bs2_photo_nl_bin': 0.0, 'b3nl_photo_nl_bin': 0.0, 'bk2_photo_nl_bin': 0.0},
}
out = {'ells': zc.ELLS}
t0 = time.time()
for name, change in VARIANTS.items():
    zc.NUIS_POS_NL.clear(); zc.NUIS_POS_NL.update(BASE)
    for prefix, val in change.items():
        for k in list(zc.NUIS_POS_NL):
            if k.startswith(prefix):
                zc.NUIS_POS_NL[k] = val
    for n_t in NT:
        for k, v in zc.check_spectra('nlbias_NLA', n_t, 255).items():
            out[f'E5|{name}|nt={n_t}|{k}'] = v
        zc._clear_jit_caches()
        print(f'[{time.time() - t0:5.0f}s] {name:22s} n_t={n_t}', flush=True)
np.savez(Path(__file__).resolve().parents[1] / 'results' / 'results_384_nlbias_NLA_E5.npz', **out)
m = zc.ELLS > 20
print(f'\nGG_1_1 error vs the same variant at n_t = 3201 [%]')
print(f'{"variant":22s} ' + ' '.join(f'{n:>7d}' for n in NT[:-1]))
for name in VARIANTS:
    ref = out[f'E5|{name}|nt=3201|GG_1_1']
    print(f'{name:22s} ' + ' '.join(f'{100 * np.max(np.abs(out[f"E5|{name}|nt={n}|GG_1_1"][m] / ref[m] - 1)):7.3f}' for n in NT[:-1]))
