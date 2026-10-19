# Redshift convergence of cloelib's Limber C_ell

Investigation of why cloelib's angular power spectra converge erratically with the
number of redshift points, found in `../../time_profiling/studies/euclid_dr3/time_comparison_Euclid_DR3.ipynb`.
In that comparison all four codes received identical 13-bin SPV3 n(z) arrays and
`N_Z` points everywhere (n(z), Limber integral, P(k,z) grid). The change of each
code's C_ell against its own `N_Z = 250` result was:

| `N_Z` | cloelib | pyccl | CosmoSIS | former CLOE |
|---|---|---|---|---|
| 100 | 6.5% | 0.5% | 0.7% | 1.1% |
| 150 | 2.0% | 0.6% | 0.2% | 0.3% |
| 200 | 2.1% | 0.5% | 0.5% | 0.5% |

The change is the maximum over six check spectra and $\ell > 20$, for TATT +
non-linear galaxy bias at $n_\ell = 32$. The largest offender is GG for bin 1,
the narrowest, lowest-z bin.

## Layout

| path | what |
|---|---|
| `scripts/zconv_common.py` | the benchmark model with the two redshift grids cloelib uses **decoupled**: tracer grid `n_t` (n(z), windows, Limber) and perturbation grid `n_p` (CAMB P(k,z), at most 255). It also provides swappable numerics: trapezoid instead of Simpson weights, and P instead of log\|P\| interpolation of signed spectra |
| `scripts/run_experiments.py`, `scripts/run_E4.py`, `scripts/run_E5.py`, `scripts/run_E6.py` | experiments E0–E6 (see their docstrings); each writes `results/results_*.npz` |
| `scripts/verify_fix.py` | re-runs the key experiments against a cloelib checkout with the fixes (`CLOELIB_SRC=<path>`) |
| `limber_z_convergence.ipynb` | analysis and figures of the saved results |
| `results/`, `logs/` | the October 2026 outputs: raw spectra (`*.npz`) and the drivers' logs. The notebook writes its figures to `figures/` (not tracked in git) |

The n(z) is `tp_paths.NZ_SPV3` (`data/nz/nzTabSPV3.fits`).

## Environment

Independent of the `cloe-cosmosis` environment used by the timing notebooks:

- **Code** (cloned by `../../time_profiling/environment/setup_external.sh`), selected with `CLOELIB_SRC`:
  - `main` (default): cloelib `main` at `a59f0a4`, `tp_paths.CLOELIB['main-a59f0a4']`;
  - `384`: the non-linear galaxy bias branch, PR #596 at `c0f36e4`, `tp_paths.CLOELIB['pr596-c0f36e4']`;
  - any other value: the path of a cloelib checkout (`verify_fix.py`).
- **Python:** the `cloelib-zconv` environment, built from `../../time_profiling/environment/cloelib-zconv-env-linux.yaml` by `../../time_profiling/environment/setup_envs.sh`. The scripts put the selected cloelib first on `sys.path` and check that it is the one imported.

```bash
cd numerical_validation/limber_z_convergence
PY=../../time_profiling/environment/envs/cloelib-zconv/bin/python
CLOELIB_SRC=main $PY scripts/run_experiments.py --model linear_NLA   # linear-bias models
CLOELIB_SRC=384  $PY scripts/run_experiments.py --model nlbias_TATT  # + non-linear bias
```

## Findings

Full analysis and figures: `limber_z_convergence.ipynb`. The reference is the tracer grid at 3201 points and the P(k,z) grid at 255 points; it is converged to 0.01% (Simpson at 3201 vs trapezoid at 3200).

1. **The benchmark's erratic GG 1-1 convergence is a zero crossing of $C_\ell$, not an integration error.**
   - With cloelib's $\sigma^4$ subtraction, the non-linear-bias GG 1-1 changes sign between $\ell \approx 2370$ and 3000.
   - All the large relative errors sit next to that crossing.
   - Measured against $|C_\ell|$ without $\sigma^4$, the integration error is 0.27 / 0.25 / 0.35 / 0.06% at N = 100 / 150 / 200 / 250. That is the same as linear bias, and in line with pyccl, CosmoSIS and former CLOE, whose GG do not subtract $\sigma^4$ and so do not cross zero.
   - Switching the $\sigma^4$ kernel off makes the convergence identical to linear bias (E6). $b_1$ and $b_{k^2}$ are innocent (E5), and the signed-spectrum interpolation is innocent too (E4).
   - Open physics question for the bias-model authors: is a negative $C^{gg}_\ell$ at $\ell \sim 3000$ expected for these (illustrative) bias values?
2. **Odd N uses the true composite Simpson rule; even N is effectively the trapezoid rule.**
   - Even N averages two shifted Simpson rules, which gives interior weights of 1. Odd N uses the alternating 4/3, 2/3 weights.
   - On the narrow bin-1 $n(z)^2$ peak that is node-placement sensitive: GG 1-1 is off by 2.8% at N = 101 and 0.8% at 151, against 0.25% at 100 and 150.
   - **Fix candidate:** one rule for both parities (`math_utils.simpsons_weights_odd`, used by `AngularTwoPoint` through `simpsons_weights_jit`).
3. **The stacked Simpson weights are wrong for the last two rows.** One point gets weight 1/3 (should be 0); two points get 2/3, 2/3 (should be 1/2, 1/2).
   - This is in `math_utils.stack_zeros_and_simpson`, used for the lensing and magnification efficiency.
   - It is small for these bins, but wrong.
4. **`cached_stacked_simpson` is `jax.jit` around a `functools.lru_cache` that caches a tracer.** It raises `UnexpectedTracerError` after `jax.clear_caches()` or any re-trace for the same n.
   - **Fix candidate:** build the weights with numpy and cache the concrete array, without `jit`.
5. **TATT EE in the lowest bin needs at least about 150 P(k,z) redshift points** for 0.1–0.2%: 1.2% at `n_p = 50`, 0.2% at 100 (E2).

Experiment drivers: `scripts/run_experiments.py` (E0–E3), `scripts/run_E4.py`, `scripts/run_E5.py`, `scripts/run_E6.py`; their raw spectra are in `results/`.

**Practical note.** One process compiling many grid sizes exhausts the kernel's memory-mapping limit (`vm.max_map_count = 65530`): a single `n_t = 3201` compilation uses about 38,000 mappings. The drivers therefore run one model per process and clear JAX's caches after every spectrum.
