"""Build the datasets of the time-profiling dashboard from the committed results.

    python build_dashboard_data.py        # -> data/*.json (one row-array file per dataset)

Every number on the dashboard comes from these files, and every file from results in this repository:
  nell_sweeps.json      euclid_dr3 (printed tables of the executed notebooks) and euclid_dr1 (results/*.json)
  analysis_setup.json   euclid_dr3/results/cloelib_*.json, cloe_{linear,pt}_nz*.json
  speedcheck.json       speedcheck_reanalysis/results/*.json, plus the speedcheck's own published numbers
  cloelib_profile.json  studies/cloelib_profiling/results/*.json (when that notebook has run)
  studies.json          provenance of each study
"""
import glob
import re as _re
import json
import os
import re
from pathlib import Path

TP = Path(__file__).resolve().parents[1]
C = TP / 'studies'
OUT = Path(__file__).resolve().parent / 'data'
OUT.mkdir(exist_ok=True)
CODES = ('cloelib', 'pyccl', 'CosmoSIS', 'CLOE (former)')


def printed_tables(nb_path):
    """(median, first call) {code: {n_ell: s}} from the DR3 notebook's printed section-4 tables."""
    nb = json.load(open(nb_path))
    for c in nb['cells']:
        for o in c.get('outputs', []):
            t = ''.join(o.get('text', ''))
            if t.startswith('One full 3x2pt evaluation from scratch'):
                med_part, first_part = t.split('First call at each ell-grid')
                parse = lambda part: {int(m[0]): list(map(float, m[1:5])) for m in
                                      re.findall(r'^\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', part, re.M)}
                return parse(med_part), parse(first_part.split('1-min load')[0])
    raise ValueError(nb_path)


rows = []
for nb, cpus in (('time_comparison_Euclid_DR3.ipynb', '128 cores'), ('time_comparison_Euclid_DR3_1core.ipynb', '1 core')):
    med, first = printed_tables(C / 'euclid_dr3' / nb)
    for n_ell, vals in med.items():
        for code, v, f in zip(CODES, vals, first[n_ell]):
            rows.append({'study': 'Euclid DR3, 13 bins', 'cpus': cpus, 'code': code, 'n_ell': n_ell,
                         'median_s': v, 'first_call_s': f})
for n in (8, 96):
    r = json.load(open(C / 'euclid_dr1' / 'results' / f'timings_Euclid_DR1_{n}cpu.json'))
    for code in CODES:
        for n_ell, v in r['results'][code].items():
            rows.append({'study': 'Euclid DR1, 6 bins', 'cpus': f'{n} CPUs', 'code': code, 'n_ell': int(n_ell),
                         'median_s': round(v, 4), 'first_call_s': round(r['first_call'][code][n_ell], 4)})
json.dump(rows, open(OUT / 'nell_sweeps.json', 'w'), indent=1)

R13 = C / 'euclid_dr3' / 'results'
rows = []
for model, label in (('linear', 'linear bias, NLA'), ('pt', 'one-loop bias, TATT')):
    lib = json.load(open(R13 / f'cloelib_{model}.json'))
    for n_z in (100, 250, 600, 1000):
        cl = json.load(open(R13 / f'cloe_{model}_nz{n_z}.json'))
        rows.append({'model': label, 'n_z': n_z, 'code': 'cloelib', 'median_s': round(lib['from_scratch'][str(n_z)]['32'], 4),
                     'first_call_s': round(lib['first_call'][str(n_z)]['32'], 4)})
        rows.append({'model': label, 'n_z': n_z, 'code': 'CLOE (former)', 'median_s': round(cl['from_scratch']['32'], 4),
                     'first_call_s': round(cl['first_call']['32'], 4)})
json.dump(rows, open(OUT / 'analysis_setup.json', 'w'), indent=1)

RS = C / 'speedcheck_reanalysis' / 'results'
ld = lambda n: json.load(open(RS / f'{n}.json'))
rows = [
    {'case': 'CLOE, their set-up', 'code': 'CLOE (former)', 'where': 'speedcheck (EPYC 7742)', 'time_s': 0.087},
    {'case': 'cloelike, June 2026', 'code': 'cloelib', 'where': 'speedcheck (EPYC 7742)', 'time_s': 0.228},
    {'case': 'cloelike, June, no JIT', 'code': 'cloelib', 'where': 'speedcheck (EPYC 7742)', 'time_s': 3.753},
    {'case': 'CLOE, their set-up', 'code': 'CLOE (former)', 'where': 're-run here',
     'time_s': round(ld('cloe_their_config')['cobaya_euclid_one_evaluation_s'], 4)},
    {'case': 'cloelike, June 2026', 'code': 'cloelib', 'where': 're-run here',
     'time_s': round(ld('cloelike_june')['median']['likelihood_only'], 4)},
    {'case': 'cloelike, June, no JIT', 'code': 'cloelib', 'where': 're-run here',
     'time_s': round(ld('cloelike_june_nojit')['median']['likelihood_only'], 4)},
    {'case': 'cloelike, today', 'code': 'cloelib', 'where': 're-run here',
     'time_s': round(ld('cloelike_main')['median']['likelihood_only'], 4)},
    {'case': 'CLOE, one-loop and TATT', 'code': 'CLOE (former)', 'where': 're-run here',
     'time_s': round(ld('cloe_tatt_nlbias')['cobaya_euclid_one_evaluation_s'], 4)},
]
json.dump(rows, open(OUT / 'speedcheck.json', 'w'), indent=1)

rows = []
for f in sorted(glob.glob(str(C / 'cloelib_profiling' / 'results' / '*.json'))):
    r = json.load(open(f))
    name = Path(f).stem
    for n_z, d in r['from_scratch'].items():
        for n_ell, v in d.items():
            row = {'run': name, 'model': r['model'], 'n_bins': r['n_bins'], 'n_cpu': r['n_cpu'], 'n_z': int(n_z),
                   'n_ell': int(n_ell), 'median_s': round(v, 4), 'first_call_s': round(r['first_call'][n_z][n_ell], 4)}
            for stage, t in r.get('breakdown', {}).get(n_z, {}).get(n_ell, {}).items():
                row['stage_' + _re.sub(r'\W+', '_', stage)] = round(t, 4)
            p = r.get('profile')
            if p and p['n_z'] == int(n_z) and p['nell'] == int(n_ell):
                row['eager_jax_dispatches'] = p['eager_jax_dispatches']
                row.update({'share_' + _re.sub(r'\W+', '_', k).strip('_'): round(v / p['total_s'], 4)
                            for k, v in p['groups_s'].items()})
            rows.append(row)
if rows:
    json.dump(rows, open(OUT / 'cloelib_profile.json', 'w'), indent=1)

studies = [
    {'study': 'Euclid DR3, 13 bins', 'folder': 'studies/euclid_dr3',
     'setup': '351 spectra, TATT + one-loop bias, N_Z 100', 'hardware': '128-core node; and 1 core (taskset)',
     'cloelib': 'PR #596 c0f36e4', 'date': '2026-10-01'},
    {'study': 'Euclid DR1, 6 bins', 'folder': 'studies/euclid_dr1',
     'setup': '78 spectra, TATT + one-loop bias, N_Z 100', 'hardware': 'AMD EPYC 9454, 8 and 96 CPUs of one NUMA node',
     'cloelib': 'PR #596 3f443c4', 'date': '2026-10-09'},
    {'study': 'Analysis set-up, 13 bins', 'folder': 'studies/euclid_dr3',
     'setup': '351 spectra, 32 ell, N_Z 100-1000, two models', 'hardware': 'AMD EPYC 9454, 8 CPUs',
     'cloelib': 'main 0966dfa', 'date': '2026-10-09'},
    {'study': 'July 2026 speedcheck, re-run', 'folder': 'studies/speedcheck_reanalysis',
     'setup': '10 bins, 20 ell, N_Z 100, linear bias + NLA', 'hardware': 'AMD EPYC 9454, 8 CPUs',
     'cloelib': '691c4f3 (June) and 0966dfa', 'date': '2026-10-09'},
]
if rows:
    studies.append({'study': 'cloelib profiling', 'folder': 'studies/cloelib_profiling',
                    'setup': '6 and 13 bins, 32-3000 ell, N_Z 100-1000, two models',
                    'hardware': f'AMD EPYC 9454, 1-{max(r["n_cpu"] for r in rows)} CPUs', 'cloelib': 'main 0966dfa',
                    'date': '2026-10'})
json.dump(studies, open(OUT / 'studies.json', 'w'), indent=1)
for f in sorted(OUT.glob('*.json')):
    print(f.name, len(json.load(open(f))), 'rows')
