# Beyond-Limber validation of cloelib

Compares the beyond-Limber angular power spectra of cloelib with Blast.jl,
pyccl and cosmosis on a synthetic setup (three Gaussian redshift bins in `config.toml`, three
Smail bins with photo-z errors in `config_smail.toml`), for
five 3x2pt setups, and plots the comparison. The cloelib under test is the
beyond-Limber branch (`feature/no-limber`) at commit `f7bfbdc`, pinned in
`[setup] cloelib`.

## Layout

| path | what |
|---|---|
| `nonlimber_validation.py` | everything: setup, shared inputs, the four codes, plots (standard library only) |
| `config.toml`, `config_smail.toml` | physics, setups, numerical settings of each code, environments: Gaussian and Smail bins |
| `local.toml` | optional, your machine only (git-ignored): overrides of `[environment]` |
| `environment/` | `cloelib.yml`, `ccl.yml`, `cosmosis.yml` (conda), `blast/` (Julia project, pinned by its `Manifest.toml`) |
| `data/<name>/` | the Cl of every code and the shared inputs (`*.npz`, in git) |
| `results/<name>/` | tables (`summary.md`, in git) and figures (`*.png`, not in git: `plots` redoes them) |
| `logs/<name>/` | the log of every task of the committed run |
| `nonlimber_validation.ipynb` | analysis and figures of the committed results, both configs (reads `data/`, computes nothing; figures to `figures/`, not in git) |
| `external/`, `.work/` | (git-ignored) the cosmosis standard library cloned by `setup`, helper files of Blast and cosmosis |

## Findings

Full analysis and figures: `nonlimber_validation.ipynb`. cloelib `f7bfbdc`, non-linear $P(k)$, beyond Limber for $\ell \leq 200$; $\sigma_\ell$ is the Gaussian error with noise ($f_{\rm sky} = 0.36$, 30 gal/arcmin$^2$, $\sigma_e = 0.3$), $\Delta\chi^2$ is for the whole 3x2pt (Knox).

1. **The beyond-Limber correction matters.** Using Limber instead changes the 3x2pt $\chi^2$ by 10–17 (Gaussian bins) and 6–10 (Smail bins) for $\ell \leq 200$.
2. **cloelib agrees with Blast.jl and pyccl for every term and both $n(z)$.** The terms are density, magnification, RSD, shear and NLA.
   - The largest difference is $\leq 1.0 \times 10^{-2}\,\sigma_\ell$ for $\ell \leq 200$.
   - $\Delta\chi^2_{\ell \leq 200} \leq 0.015$ in every setup, about a thousandth of the correction.
3. **Above $\ell = 200$, cloelib keeps RSD in its Limber spectra.** CosmoSIS does not, and pyccl's Limber RSD is about 60x smaller.
   - This, not the beyond-Limber part, is why pyccl's $\Delta\chi^2$ up to $\ell = 1000$ is 0.19 (Gaussian bins) in the setups with RSD.
   - At $\ell = 206$ Blast is still beyond Limber, and its RSD effect agrees with cloelib's (0.51% vs 0.40% of $C_\ell$ in bin 3).
4. **Blast.jl uses its own Limber above $\ell = 220$.** That accounts for all of its $\Delta\chi^2_{\ell \leq 1000}$ = 0.01–0.03.
5. **CosmoSIS is a reference only for galaxy density and RSD.** POS-POS agrees to $\leq 1.7 \times 10^{-2}\,\sigma$. Its shear, magnification and IA are low at $\ell \lesssim 20$, up to $0.31\,\sigma$, because it puts Limber lensing kernels inside the exact integral.

## Requirements

- Linux or macOS with `bash` and `git`;
- conda, mamba or micromamba (found automatically, or `[environment] conda`);
- Julia >= 1.10 on the PATH (or `[environment] julia`), for Blast;
- any `python3` >= 3.11 to launch the script (standard library only);
- network access on the first run: the environments, cloelib, the cosmosis
  standard library (~800 MB), the Julia packages, and the T-tilde dataset that
  cloelib downloads from Zenodo (1.8 GB);
- access to the cloelib repository at `[setup] cloelib` (the commit with the
  beyond-Limber code).

## Use

```bash
python3 nonlimber_validation.py setup --dry-run   # what setup would do
python3 nonlimber_validation.py setup             # environments, cloelib, cosmosis library, Julia
python3 nonlimber_validation.py run               # inputs, cloelib, ccl, blast, cosmosis, plots (~10 min)
python3 nonlimber_validation.py run --codes cloelib  # recompute only some codes, then the plots
python3 nonlimber_validation.py plots             # only plots and tables, from the saved Cl
python3 nonlimber_validation.py run config_smail.toml  # another config: three Smail bins (results/smail/)
```

`setup` creates three conda environments (`nlv-cloelib`, `nlv-ccl`,
`nlv-cosmosis`) from `environment/*.yml`, installs cloelib in the first,
clones the cosmosis standard library at the pinned commit into
`external/`, and instantiates the Julia project of Blast (versions pinned by
`environment/blast/Manifest.toml`). Existing environments are left as they are
(`--force` updates them).

Every code runs in its own environment: the script calls itself there
(`... worker <task>`), so no environment needs the packages of the others.

### Your own environments

To reuse environments you already have, write a `local.toml` next to the
config (do not share it), e.g.

```toml
[environment]
conda = "~/miniforge3/bin/conda"
cloelib = { python = "/path/to/venv/bin/python" }   # or { conda = "my-env" }
ccl = { conda = "my-ccl-env" }
cosmosis = { conda = "my-cosmosis-env" }
cosmosis_standard_library = "/path/to/cosmosis-standard-library"
cloelib_path = "/path/to/cloelib"   # a source tree to import instead of the installed cloelib
```

`setup` then creates nothing for these entries and does not install cloelib
into an environment it did not create.

## Outputs

The Cl are saved once, so figures and tables can be redone at any time with
`plots`, without recomputing anything:

- `data/<name>/<code>.npz`: the Cl of each code, key `"<setup>__<probe>/<mode>"`
  (probe gg, gs, ss; mode `limber`, `nonlimber`, `limber_lin`,
  `nonlimber_lin`), shape `(n_ell, n_bin_a, n_bin_b)`, plus `ells`, the config
  and the metadata: version (cloelib: path, home as `~`, commit, uncommitted changes;
  Blast: repository and revision; cosmosis: standard-library commit),
  numerical settings, run times, provenance (date, machine, sha256 of the
  script and of the inputs). `inputs.npz`: the shared P(k, z), background,
  n(z), parameters (CAMB).
- `results/<name>/<setup>/`, per mode of `[plots] modes`; every figure has a
  title with the terms of the setup, a subtitle that says what is plotted, and
  a note in the panels where a code has no value (with the reason):
  `cl__<mode>.png` (Cl of every bin pair, every code, and cloelib with Limber
  at every ell), `delta_sigma__<mode>.png` ((C_code - C_cloelib) / sigma_ij,
  Gaussian error with noise; same axis in every panel, linear within 1e-3 and
  logarithmic outside), `maer__<mode>.png` (100 |dC| / sigma_CV of the diagonal
  pairs, one row per code, POS-POS, POS-SHE, SHE-SHE; same logarithmic axis in
  every panel), `summary.md` (maximum residuals and Delta chi^2 of the 3x2pt
  per code).
- `results/<name>/summary.md`: all the tables and the versions of every code.
- `logs/<name>/<task>.log`.

## Setups

| folder | galaxy terms | shear terms |
|---|---|---|
| `1_density_x_shear` | density | shear |
| `2_density-magnification_x_shear` | density, magnification | shear |
| `3_density-rsd_x_shear` | density, RSD | shear |
| `4_density_x_shear-ia` | density | shear, NLA |
| `5_density-magnification-rsd_x_shear-ia` | density, magnification, RSD | shear, NLA |

Change them, or the physics, the multipoles and the settings of each code, in
`config.toml`: every code reads the same file.

## What the codes compute

The non-linear Cl is C = C_Limber^NL + (C_nonLimber^lin - C_Limber^lin) below
the transition to Limber, C_Limber^NL above, in every code; all of them read
the same tabulated P(k, z) and background.

| code | beyond Limber | transition |
|---|---|---|
| cloelib | T-tilde method (arXiv:2609.01855), all terms | `ell_nonlimber_max` (200) |
| Blast.jl | T-tilde method, same dataset, independent implementation | fixed 220; no RSD in its Limber part |
| pyccl | FKEM, all tracers | largest config ell <= 200 (185) |
| cosmosis | `project_2d`, `do_exact` | 200 |

Known limitations of the references: cosmosis puts the Limber lensing kernels
inside its exact integral (low at ell < ~20 for shear, magnification and IA:
not a beyond-Limber reference for them), and cannot compute RSD x
magnification, galaxy RSD x shear and magnification x IA (left out, with the
reason in the plots); CCL's FKEM has a known error at the lowest ells for the
z = 1.5 bin, and its Limber with RSD is NaN at the lowest ells for the highest-z bin
(ell = 2 with the Gaussian bins, ell <= 7 with the Smail bins: those ells are
left out of CCL's residuals and marked in the plots);
Blast's non-linear shear departs from the others above ell = 220 (its Limber
part).
