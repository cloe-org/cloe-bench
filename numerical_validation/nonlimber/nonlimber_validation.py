#!/usr/bin/env python3
"""Beyond-Limber validation of cloelib against Blast.jl, pyccl and cosmosis.

One script, one config (config.toml, plus an optional local.toml with
machine-specific overrides of [environment]):

    python3 nonlimber_validation.py setup [--dry-run] [--force]
        Create the environments (environment/*.yml, conda), install cloelib
        ([setup] cloelib), clone the cosmosis standard library at a fixed
        commit, instantiate the Julia project of Blast (environment/blast).
    python3 nonlimber_validation.py run [--codes cloelib ccl ...] [--inputs]
        Shared inputs (if missing, or with --inputs), every code of `run` in
        its own environment, then the plots.
    python3 nonlimber_validation.py plots
        Only the plots and tables, from data/<name>/*.npz.

Any python >= 3.11 can drive it (standard library only): every task runs in
the environment of its code, by calling this same script
(`... worker <task> <config>`), so no environment needs the packages of the
others.

What every code computes (the non-linear Cl is
C = C_Limber^NL + (C_nonLimber^lin - C_Limber^lin) below the transition,
C_Limber^NL above, in every code):
- cloelib: AngularTwoPoint(..., ell_nonlimber_max), T-tilde method
  (arXiv:2609.01855), all terms beyond Limber;
- Blast.jl: T-tilde method, same dataset, independent implementation; fixed
  transition at ell = 220, no RSD in its Limber part;
- pyccl: FKEM, all tracers, l_limber = largest config ell <= ell_nonlimber_max;
- cosmosis: project_2d with do_exact; it cannot compute RSD x magnification,
  galaxy RSD x shear and magnification x IA (left out, with the reason), and
  its exact integral uses Limber lensing kernels inside the Bessel integral
  (low at ell < ~20 for shear, magnification, IA: not a beyond-Limber
  reference for those).

Outputs (next to the config): data/<name>/<code>.npz (the Cl, key
"<setup>__<probe>/<mode>", shape (n_ell, n_bin_a, n_bin_b), with the config,
settings, run times and provenance), results/<name>/<setup>/ (cl, delta_sigma,
maer figures and summary.md), results/<name>/summary.md, logs/<name>/.
"""

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve()
CODES = ("cloelib", "ccl", "blast", "cosmosis")
MODES = ("limber", "nonlimber", "limber_lin", "nonlimber_lin")
PROBES = {"gg": ("g", "g"), "gs": ("g", "s"), "ss": ("s", "s")}
TITLES = {"gg": "POS-POS", "gs": "POS-SHE", "ss": "SHE-SHE"}
C_KMS = 299792.458


# =========================================================================== config


def _merge(base, override):
    """`override` on top of `base`, table by table: a key of a table of
    `override` replaces the same key of `base` (e.g. a whole
    [environment] cloelib = {...} entry)."""
    out = dict(base)
    for key, value in override.items():
        out[key] = {**out[key], **value} if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def load_config(path="config.toml"):
    """The config, merged with local.toml (if next to it); root = its folder."""
    path = Path(path).resolve()
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    local = path.parent / "local.toml"
    if local.exists():
        with open(local, "rb") as f:
            cfg = _merge(cfg, tomllib.load(f))
    cfg["_path"] = str(path)
    cfg["_root"] = str(path.parent)
    return cfg


def root(cfg):
    return Path(cfg["_root"])


def resolve(cfg, path):
    path = Path(os.path.expanduser(path))
    return path if path.is_absolute() else root(cfg) / path


def data_dir(cfg):
    path = root(cfg) / "data" / cfg["name"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def inputs_path(cfg):
    return data_dir(cfg) / "inputs.npz"


def ells(cfg):
    """Integer, log-spaced, unique multipoles."""
    import numpy as np

    e = cfg["ells"]
    return np.unique(np.round(np.geomspace(e["ell_min"], e["ell_max"], e["n_ell"])).astype(int))


def setups(cfg):
    """{'<step>_<galaxy terms>_x_<shear terms>': (galaxy terms, shear terms)}."""
    out = {}
    for i, s in enumerate(cfg["setups"]):
        galaxy, shear = tuple(s["galaxy"]), tuple(s["shear"])
        out[f"{i + 1}_{'-'.join(galaxy)}_x_{'-'.join(shear)}"] = (galaxy, shear)
    return out


def case_name(setup, probe):
    return f"{setup}__{probe}"


def cases(cfg):
    """{case: (tracer a, tracer b, galaxy terms, shear terms)}, one per probe of each setup."""
    return {
        case_name(name, probe): (a, b, galaxy, shear)
        for name, (galaxy, shear) in setups(cfg).items()
        for probe, (a, b) in PROBES.items()
    }


def load_inputs(cfg):
    import numpy as np

    with np.load(inputs_path(cfg)) as data:
        return {key: data[key] for key in data.files}


# =========================================================================== bookkeeping


class Timings:
    """Wall-clock time of the steps of a run, and of the whole run."""

    def __init__(self, code):
        self.code, self.start, self.steps = code, time.perf_counter(), {}

    @contextmanager
    def __call__(self, label):
        start = time.perf_counter()
        yield
        self.steps[label] = self.steps.get(label, 0.0) + time.perf_counter() - start
        print(f"[{self.code}] {label}: {self.steps[label]:.1f} s", flush=True)

    def as_dict(self):
        return {"total": time.perf_counter() - self.start, "steps": self.steps}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance(cfg):
    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": platform.node(),
        "python": platform.python_version(),
        "script_sha256": sha256(SCRIPT),
        "inputs_sha256": sha256(inputs_path(cfg)),
    }


def save_cls(cfg, code, cls, meta):
    import numpy as np

    valid = cases(cfg)
    for (case, mode), cl in cls.items():
        if case not in valid or mode not in MODES or np.shape(cl)[0] != len(ells(cfg)):
            raise ValueError(f"{code}: unexpected {case}/{mode} of shape {np.shape(cl)}.")
    meta = {**meta, "provenance": provenance(cfg)}
    path = data_dir(cfg) / f"{code}.npz"
    np.savez(
        path,
        ells=ells(cfg),
        config=json.dumps({k: v for k, v in cfg.items() if not k.startswith("_")}),
        meta=json.dumps(meta),
        **{f"{case}/{mode}": np.asarray(cl) for (case, mode), cl in cls.items()},
    )
    print(f"[{code}] saved {len(cls)} spectra to {path}", flush=True)


def load_cls(cfg, code):
    import numpy as np

    with np.load(data_dir(cfg) / f"{code}.npz") as data:
        cls = {tuple(key.split("/")): data[key] for key in data.files if "/" in key}
        return cls, json.loads(str(data["meta"]))


# =========================================================================== shared inputs (CAMB)


def redshift_bins(nz):
    """(z, n_i(z)) of the [nz] config, each bin normalized to 1.

    kind "gaussian": n_i ∝ exp(-(z - mean_i)^2 / 2 sigma_i^2), sigma_i = sigma0 (1 + mean_i).
    kind "smail": parent n(z) ∝ (z/z0)^alpha exp(-(z/z0)^beta), z0 = z_m / sqrt(2), cut in
    photometric redshift between the `edges` (a list, or "equipopulated" with `n_bins`) and
    convolved with the photo-z error p(z_p|z): a Gaussian of width sigma (1 + z), plus a
    fraction f_out of outliers shifted by z_out with width sigma_out (1 + z).
    """
    import numpy as np
    from scipy.special import erf

    z = np.linspace(nz["z_min"], nz["z_max"], nz["n_z"])
    if nz["kind"] == "gaussian":
        bins = np.array([np.exp(-0.5 * ((z - m) / (nz["sigma0"] * (1 + m))) ** 2) for m in nz["means"]])
    elif nz["kind"] == "smail":
        z0 = nz["z_m"] / np.sqrt(2.0)
        parent = (z / z0) ** nz["alpha"] * np.exp(-((z / z0) ** nz["beta"]))
        edges = nz["edges"]
        if edges == "equipopulated":
            cdf = np.concatenate([[0.0], np.cumsum(0.5 * (parent[1:] + parent[:-1]) * np.diff(z))])
            edges = np.interp(np.linspace(0.0, 1.0, nz["n_bins"] + 1), cdf / cdf[-1], z)
        edges = np.asarray(edges, float)

        def in_bin(lo, hi, shift, sigma):
            # P(lo < z_p < hi | z), z_p ~ N(z - shift, sigma (1 + z))
            w = np.sqrt(2.0) * sigma * (1 + z)
            return 0.5 * (erf((hi - z + shift) / w) - erf((lo - z + shift) / w))

        f_out = nz.get("f_out", 0.0)
        bins = np.array([
            parent * ((1 - f_out) * in_bin(lo, hi, 0.0, nz["sigma"])
                      + f_out * in_bin(lo, hi, nz.get("z_out", 0.0), nz.get("sigma_out", nz["sigma"])))
            for lo, hi in zip(edges[:-1], edges[1:])
        ])
        print(f"[inputs] Smail bins, photometric edges {np.round(edges, 4).tolist()}", flush=True)
    else:
        raise ValueError(f"Unsupported n(z) kind {nz['kind']!r}: 'gaussian' or 'smail'.")
    return z, bins / np.trapezoid(bins, z, axis=1)[:, None]


def task_inputs(cfg):
    """data/<name>/inputs.npz: P(k, z) (linear, non-linear), background, n(z), parameters."""
    import camb
    import numpy as np

    c, t = cfg["cosmology"], cfg["tables"]
    pars = camb.set_params(
        H0=100 * c["h"], ombh2=c["Omega_b"] * c["h"] ** 2, omch2=c["Omega_c"] * c["h"] ** 2,
        mnu=c["mnu"], num_massive_neutrinos=1 if c["mnu"] > 0 else 0, ns=c["n_s"], As=c["A_s"],
        tau=c["tau"], w=c["w0"], wa=c["wa"], dark_energy_model="ppf", halofit_version=c["halofit"],
        WantTransfer=True, kmax=t["k_max"] * 1.2, redshifts=list(np.linspace(t["z_max"], 0.0, 150)),
    )
    results = camb.get_results(pars)
    z_pk = np.linspace(0.0, t["z_max"], t["n_z"])
    k = np.geomspace(t["k_min"], t["k_max"], t["n_k"])
    pk = {}
    for key, nonlinear in [("pk_lin", False), ("pk_nl", True)]:
        interp = camb.get_matter_power_interpolator(
            pars, nonlinear=nonlinear, hubble_units=False, k_hunit=False, kmax=t["k_max"] * 1.2,
            zmax=t["z_max"], var1="delta_tot", var2="delta_tot",
        )
        pk[key] = interp.P(z_pk, k)
    z_bg = np.linspace(0.0, t["z_max"], 2000)
    lin = camb.get_matter_power_interpolator(pars, nonlinear=False, hubble_units=False, k_hunit=False,
                                             zmax=t["z_max"])
    D = np.sqrt(lin.P(z_bg, 1e-3) / lin.P(0.0, 1e-3))  # scale-independent growth (massless nu)
    background = {
        "z_bg": z_bg, "chi": results.comoving_radial_distance(z_bg), "H": results.hubble_parameter(z_bg),
        "D": D, "f": -np.gradient(np.log(D), np.log(1.0 + z_bg)),
    }
    z_nz, bins = redshift_bins(cfg["nz"])
    gal = cfg["galaxies"]
    if not len(gal["bias"]) == len(gal["s"]) == len(bins):
        raise ValueError("bias, s and the n(z) must have one entry per bin.")
    np.savez(
        inputs_path(cfg), z_pk=z_pk, k=k, **pk, **background, z_nz=z_nz, nz_lens=bins, nz_source=bins.copy(),
        bias=np.asarray(gal["bias"], float), s=np.asarray(gal["s"], float), h=c["h"], Omega_b=c["Omega_b"],
        Omega_c=c["Omega_c"], Omega_m=c["Omega_b"] + c["Omega_c"], n_s=c["n_s"], A_s=c["A_s"],
        sigma8=results.get_sigma8_0(), camb_version=camb.__version__,
    )
    print(f"[inputs] saved {inputs_path(cfg)} (CAMB {camb.__version__})", flush=True)


# =========================================================================== cloelib


def cloelib_provenance():
    """Version and commit of the cloelib that is imported."""
    import importlib.metadata

    import cloelib

    path = Path(cloelib.__file__).resolve().parent
    # The home directory as "~": the metadata are committed with the results.
    out = {"path": str(path).replace(str(Path.home()), "~", 1), "version": getattr(cloelib, "__version__", None)}

    def git(*args):
        try:
            return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True,
                                  text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    commit = git("rev-parse", "HEAD")
    if commit:
        out.update(commit=commit, branch=git("rev-parse", "--abbrev-ref", "HEAD"),
                   dirty=bool(git("status", "--porcelain", "--", ".")))
        return out
    try:
        direct = json.loads(importlib.metadata.distribution("cloelib").read_text("direct_url.json") or "{}")
        out.update(url=direct.get("url"), commit=direct.get("vcs_info", {}).get("commit_id"))
    except importlib.metadata.PackageNotFoundError:
        pass
    return out


def task_cloelib(cfg):
    extra = cfg["environment"].get("cloelib_path", "")
    if extra:
        sys.path.insert(0, str(resolve(cfg, extra)))
    import interpax
    import jax
    import jax.numpy as jnp
    import numpy as np

    from cloelib.cosmology.cosmology import CB_CROSS_CORRELATED
    from cloelib.observables.photo import PositionsTracer, ShearTracer
    from cloelib.summary_statistics.angular_two_point import AngularTwoPoint

    jax.config.update("jax_enable_x64", True)

    class Background:
        """Flat background from the tabulated chi(z), H(z) (km/s/Mpc)."""

        def __init__(self, inputs):
            self._z, self._chi, self._H = (jnp.asarray(inputs[k]) for k in ("z_bg", "chi", "H"))
            self.h = float(inputs["h"])
            self.H0 = 100.0 * self.h
            self.Omega_b0, self.Omega_cdm0 = float(inputs["Omega_b"]), float(inputs["Omega_c"])
            self.Omega_k0, self.mnu, self.N_mnu = 0.0, 0.0, 0
            self.As, self.ns = float(inputs["A_s"]), float(inputs["n_s"])
            self.w0, self.wa, self.gamma_MG = -1.0, 0.0, 0.0

        def hubble_parameter(self, zs, units="km/s/Mpc"):
            H = jnp.interp(jnp.asarray(zs), self._z, self._H)
            if units == "km/s/Mpc":
                return H
            if units == "1/Mpc":
                return H / C_KMS
            raise ValueError(f"Unsupported units {units!r}.")

        def comoving_distance(self, zs):
            return jnp.interp(jnp.asarray(zs), self._z, self._chi)

        def transverse_comoving_distance(self, zs):
            return self.comoving_distance(zs)

        def Omega_m(self, zs):
            E2 = (self.hubble_parameter(zs) / self.H0) ** 2
            return (self.Omega_b0 + self.Omega_cdm0) * (1 + jnp.asarray(zs)) ** 3 / E2

        def Omega_b(self, zs):
            return self.Omega_m(zs) * self.Omega_b0 / (self.Omega_b0 + self.Omega_cdm0)

        def Omega_cb(self, zs):
            return self.Omega_m(zs)

    class Perturbations:
        """Tabulated P(k, z) (cubic in (z, log k) of log P), D(z), f(z)."""

        cb_cross_prescription = CB_CROSS_CORRELATED

        def __init__(self, inputs, background, pk_key, linear=None):
            self.background = background
            self.z, self.k = jnp.asarray(inputs["z_pk"]), jnp.asarray(inputs["k"])
            self._log_k, self._log_pk = jnp.log(self.k), jnp.log(jnp.asarray(inputs[pk_key]))
            self._z_bg, self._D, self._f = (jnp.asarray(inputs[k]) for k in ("z_bg", "D", "f"))
            self._sigma8 = float(inputs["sigma8"])
            if linear is not None:
                self.linearperturbations = linear

        def matter_power_spectrum(self, zs, ks):
            zs = jnp.clip(jnp.atleast_1d(jnp.asarray(zs)), self.z[0], self.z[-1])
            log_k = jnp.clip(jnp.log(jnp.atleast_1d(jnp.asarray(ks))), self._log_k[0], self._log_k[-1])
            Z, K = jnp.meshgrid(zs, log_k, indexing="ij")
            log_pk = interpax.interp2d(Z.ravel(), K.ravel(), self.z, self._log_k, self._log_pk, method="cubic")
            return jnp.exp(log_pk).reshape(Z.shape)

        def matter_power_spectrum_cb(self, zs, ks):
            return self.matter_power_spectrum(zs, ks)  # massless neutrinos

        def growth_factor(self, zs, ks=None):
            return jnp.interp(jnp.asarray(zs), self._z_bg, self._D)

        def growth_rate(self, zs=None, ks=None):
            zs = self.z if zs is None else zs
            f = jnp.interp(jnp.asarray(zs), self._z_bg, self._f)
            return f if ks is None else jnp.broadcast_to(f[:, None], (len(f), len(ks)))

        def sigma8_0(self):
            return self._sigma8

    # cloelib recognizes a linear backend by its `*LinearPerturbations` name.
    class TabulatedLinearPerturbations(Perturbations):
        def __init__(self, inputs, background):
            super().__init__(inputs, background, "pk_lin")

    class TabulatedNonLinearPerturbations(Perturbations):
        def __init__(self, inputs, background, linear):
            super().__init__(inputs, background, "pk_nl", linear)

    def positions(pert, inputs, terms):
        n = len(inputs["bias"])
        mag = 5.0 * inputs["s"] - 2.0 if "magnification" in terms else np.zeros(n)
        nuisance = {
            **{f"dz_pos_{i + 1}": 0.0 for i in range(n)},
            **{f"width_pos_{i + 1}": 1.0 for i in range(n)},
            **{f"magnification_bias_{i + 1}": float(mag[i]) for i in range(n)},
            **{f"b1_photo_bin{i}": float(inputs["bias"][i]) for i in range(n)},
        }
        return PositionsTracer(pert, jnp.asarray(inputs["nz_lens"]), jnp.asarray(inputs["z_nz"]),
                               "per_bin", nuisance, include_rsd="rsd" in terms)

    def shear(pert, inputs, terms):
        n = len(inputs["nz_source"])
        ia = cfg["intrinsic_alignments"]
        nuisance = {
            **{f"multiplicative_bias_{i + 1}": 0.0 for i in range(n)},
            **{f"dz_shear_{i + 1}": 0.0 for i in range(n)},
            **{f"width_shear_{i + 1}": 1.0 for i in range(n)},
            "AIA": ia["A_IA"] if "ia" in terms else 0.0, "CIA": ia["C1_rhocrit"], "EtaIA": 0.0,
        }
        return ShearTracer(perturbations=pert, dndz=jnp.asarray(inputs["nz_source"]),
                           z=jnp.asarray(inputs["z_nz"]), nuisance_params=nuisance, ia_model="NLA")

    timings = Timings("cloelib")
    with timings("setup"):
        inputs = load_inputs(cfg)
        background = Background(inputs)
        linear = TabulatedLinearPerturbations(inputs, background)
        nonlinear = TabulatedNonLinearPerturbations(inputs, background, linear)
        ks, ell = jnp.asarray(inputs["k"]), jnp.asarray(ells(cfg), dtype=float)
        ell_max = cfg["ells"]["ell_nonlimber_max"]
    cls = {}
    for case, (a, b, g_terms, s_terms) in cases(cfg).items():
        for suffix, pert in [("", nonlinear), ("_lin", linear)]:
            def tracer(kind):
                return positions(pert, inputs, g_terms) if kind == "g" else shear(pert, inputs, s_terms)

            t_a = tracer(a)
            t_b = t_a if a == b else tracer(b)
            with timings(f"{case}/limber{suffix}"):
                cls[case, "limber" + suffix] = np.asarray(AngularTwoPoint(t_a, t_b).get_Cl_tensor(ell, None, ks))
            with timings(f"{case}/nonlimber{suffix}"):
                cls[case, "nonlimber" + suffix] = np.asarray(
                    AngularTwoPoint(t_a, t_b, ell_nonlimber_max=ell_max).get_Cl_tensor(ell, None, ks))
    save_cls(cfg, "cloelib", cls, {
        "version": cloelib_provenance(),
        "settings": {"ell_nonlimber_max": ell_max, "t_tildes": "T_tildes_128_64_161 (Zenodo 21717794)"},
        "timings": timings.as_dict(),
    })


# =========================================================================== pyccl


def task_ccl(cfg):
    import numpy as np
    import pyccl as ccl

    settings = cfg.get("codes", {}).get("ccl", {})
    n_samples = int(settings.get("n_samples", 2000))
    fkem_nchi = int(settings.get("fkem_nchi", 8000))
    fkem_chi_min = float(settings.get("fkem_chi_min", 1e-6))
    limber_method = settings.get("limber_integration_method", "spline")
    failures = []

    inputs = load_inputs(cfg)
    timings = Timings("ccl")
    with timings("setup"):
        a_bg = 1.0 / (1.0 + inputs["z_bg"][::-1])
        a_pk = 1.0 / (1.0 + inputs["z_pk"][::-1])
        h = float(inputs["h"])
        cosmo = ccl.CosmologyCalculator(
            Omega_c=float(inputs["Omega_c"]), Omega_b=float(inputs["Omega_b"]), h=h,
            n_s=float(inputs["n_s"]), A_s=float(inputs["A_s"]), m_nu=0.0,
            background={"a": a_bg, "chi": inputs["chi"][::-1], "h_over_h0": inputs["H"][::-1] / (100.0 * h)},
            growth={"a": a_bg, "growth_factor": inputs["D"][::-1], "growth_rate": inputs["f"][::-1]},
            **{name: {"a": a_pk, "k": inputs["k"], "delta_matter:delta_matter": inputs[key][::-1]}
               for name, key in [("pk_linear", "pk_lin"), ("pk_nonlin", "pk_nl")]},
        )
        ell = ells(cfg)
        # Largest config ell in the non-Limber range (FKEM computes every ell up
        # to and including the first one >= l_limber; a Python int, or 'auto').
        l_limber = int(ell[ell <= cfg["ells"]["ell_nonlimber_max"]].max())
        pk_lin, pk_nl = cosmo.get_linear_power(), cosmo.get_nonlin_power()

    z = inputs["z_nz"]
    one = np.ones_like(z)

    def tracers(kind, terms):
        """Per bin, the CCL tracers whose Cl add up to the bin's Cl (density +
        RSD and magnification apart: CCL's Limber integral fails at ell < 8 when
        RSD and magnification share a tracer; the Cl is bilinear, the split exact)."""
        if kind == "g":
            out = []
            for nz, b, s in zip(inputs["nz_lens"], inputs["bias"], inputs["s"]):
                parts = [ccl.NumberCountsTracer(cosmo, dndz=(z, nz), bias=(z, b * one), has_rsd="rsd" in terms,
                                                n_samples=n_samples)]
                if "magnification" in terms:
                    parts.append(ccl.NumberCountsTracer(cosmo, dndz=(z, nz), bias=None, mag_bias=(z, s * one),
                                                        has_rsd=False, n_samples=n_samples))
                out.append(parts)
            return out
        a_ia = cfg["intrinsic_alignments"]["A_IA"]
        return [[ccl.WeakLensingTracer(cosmo, dndz=(z, nz), ia_bias=(z, a_ia * one) if "ia" in terms else None,
                                       n_samples=n_samples)] for nz in inputs["nz_source"]]

    def angular_cl(t1, t2, label, **kwargs):
        def cl(ell_):
            return sum(ccl.angular_cl(cosmo, p1, p2, ell_, limber_integration_method=limber_method, **kwargs)
                       for p1 in t1 for p2 in t2)

        try:
            return cl(ell)
        except ccl.CCLError:  # e.g. Limber with RSD at ell = 2 for the high-z bin: ell by ell
            out = np.full(len(ell), np.nan)
            lim = kwargs.get("l_limber", -1)
            for n, l in enumerate(ell):
                if lim > 0 and l == lim:
                    kwargs["l_limber"] = int(l) + 1
                try:
                    out[n] = cl(np.array([l]))[0]
                except ccl.CCLError:
                    pass
                finally:
                    kwargs["l_limber"] = lim
            failures.append(f"{label}: NaN at ell = {ell[np.isnan(out)].tolist()}")
            return out

    def matrix(ta, tb, symmetric, label, **kwargs):
        out = np.zeros((len(ell), len(ta), len(tb)))
        for i, t1 in enumerate(ta):
            for j, t2 in enumerate(tb):
                if symmetric and j < i:
                    out[:, i, j] = out[:, j, i]
                else:
                    out[:, i, j] = angular_cl(t1, t2, f"{label} ({i}, {j})", **kwargs)
        return out

    cls = {}
    for case, (a, b, g_terms, s_terms) in cases(cfg).items():
        with timings(f"{case}/tracers"):
            ta = tracers(a, g_terms if a == "g" else s_terms)
            tb = ta if a == b else tracers(b, s_terms)
        for suffix, pk in [("", pk_nl), ("_lin", pk_lin)]:
            with timings(f"{case}/limber{suffix}"):
                cls[case, "limber" + suffix] = matrix(ta, tb, a == b, f"{case}/limber{suffix}",
                                                      p_of_k_a=pk, l_limber=-1)
            with timings(f"{case}/nonlimber{suffix}"):
                cls[case, "nonlimber" + suffix] = matrix(
                    ta, tb, a == b, f"{case}/nonlimber{suffix}", p_of_k_a=pk, p_of_k_a_lin=pk_lin,
                    l_limber=l_limber, non_limber_integration_method="FKEM", fkem_Nchi=fkem_nchi,
                    fkem_chi_min=fkem_chi_min)
    for failure in failures:
        print("[ccl]", failure)
    save_cls(cfg, "ccl", cls, {
        "version": ccl.__version__, "l_limber": l_limber, "failures": failures, "timings": timings.as_dict(),
        "settings": {"n_samples": n_samples, "fkem_Nchi": fkem_nchi, "fkem_chi_min": fkem_chi_min,
                     "limber_integration_method": limber_method,
                     "nonlimber": "FKEM on every tracer for ell < l_limber, Limber above"},
    })


# =========================================================================== Blast.jl

BLAST_JL = r'''
# Blast.jl Cl of the validation, written and driven by nonlimber_validation.py.
# Usage: julia --project=<environment/blast> run_blast.jl <request.toml>
using Blast
using NPZ
using TOML

const request = TOML.parsefile(ARGS[1])
const t_start = time()
const timings = Dict{String, Float64}()

function timed(f, label)
    t0 = time()
    result = f()
    timings[label] = get(timings, label, 0.0) + time() - t0
    println("[blast] $label: $(round(timings[label], digits=1)) s")
    return result
end

const inputs = npzread(request["inputs"])

cosmo = Blast.w0waCDMCosmology(
    ln10Aₛ=log(1e10 * inputs["A_s"]), nₛ=inputs["n_s"], h=inputs["h"],
    ωb=inputs["Omega_b"] * inputs["h"]^2, ωc=inputs["Omega_c"] * inputs["h"]^2,
    ωk=0.0, mν=0.0, w0=-1.0, wa=0.0,
)

# The shared background (chi, H, D, f) in place of Blast's own.
function shared_background(cosmo, inputs)
    z_tab, χ_tab = inputs["z_bg"], inputs["chi"]
    z_of_χ = Blast._make_z_of_χ(z_tab, χ_tab)
    z = z_of_χ(Blast.χ)
    interp(values) = Blast.akima_interpolation(values, z_tab, z)
    D = interp(inputs["D"])  # D(0) = 1, so D and D_norm coincide
    return Blast.Background(cosmo, z, collect(Blast.χ), interp(inputs["H"]), D, D, interp(inputs["f"]), z_of_χ)
end

bg = timed(() -> shared_background(cosmo, inputs), "setup/background")

# The shared P(k, z) (z, k in 1/Mpc) on Blast's grids (Akima in log10 k and z).
function on_grid(pk, z, log10_k)
    in_k = Blast.akima_interpolation(permutedims(log.(pk)), log10.(inputs["k"]), collect(log10_k))
    return exp.(Blast.akima_interpolation(permutedims(in_k), inputs["z_pk"], collect(z)))
end

pk_lin_nonlimber, pk_lin_limber, pk_nl_limber = timed("setup/pk_on_grids") do
    (on_grid(inputs["pk_lin"], Blast.z_lin, Blast.k_cheb),
     on_grid(inputs["pk_lin"], Blast.z_cheb, Blast.k_limber),
     on_grid(inputs["pk_nl"], Blast.z_cheb, Blast.k_limber))
end

zn = inputs["z_nz"]
nz_g, nz_s = inputs["nz_lens"], inputs["nz_source"]
n_g = size(nz_g, 1)
nbg = length(bg.z)
bias = inputs["bias"] .* ones(n_g, nbg)
s = inputs["s"] .* ones(n_g, nbg)

function galaxy_clustering(terms)
    kwargs = Dict{Symbol, Any}(:δ => Blast.NumberCounts(nz=nz_g, z=zn, bias=bias))
    "rsd" in terms && (kwargs[:RSD] = Blast.RedshiftSpaceDistortions(nz=nz_g, z=zn, growth_rate=bg.f))
    "magnification" in terms && (kwargs[:μ] = Blast.MagnificationBias(nz=nz_g, z=zn, s=s))
    return Blast.prepare_probe(Blast.GalaxyClustering(; kwargs...), bg)
end

function weak_lensing(terms)
    γ = Blast.CosmicShear(nz=nz_s, z=zn)
    if "ia" in terms
        IA = Blast.IntrinsicAlignment(nz=nz_s, z=zn, A=request["A_IA"], C1=request["C1_rhocrit"])
        return Blast.prepare_probe(Blast.WeakLensing(γ=γ, IA=IA), bg)
    end
    return Blast.prepare_probe(Blast.WeakLensing(γ=γ), bg)
end

ell = Float64.(request["ells"])
out = Dict{String, Array{Float64, 3}}()
for (case, spec) in request["cases"]
    a, b = spec["a"], spec["b"]
    used, W0, plans = timed("$case/setup") do
        probes = Dict{String, Any}()
        "g" in (a, b) && (probes["g"] = galaxy_clustering(spec["g_terms"]))
        "s" in (a, b) && (probes["s"] = weak_lensing(spec["s_terms"]))
        used = a == b ? (probes[a],) : (probes[a], probes[b])
        (used, Blast.SetUp(used...)...)
    end
    # "nonlimber": non-linear Limber correction on; "nonlimber_lin": linear P also as the non-linear one.
    for (mode, pk_nl) in (("nonlimber", pk_nl_limber), ("nonlimber_lin", pk_lin_limber))
        out["$case/$mode"] = timed("$case/$mode") do
            Pk = Blast.prepare_pk_workspace(plans, pk_lin_nonlimber, pk_lin_limber, pk_nl, bg)
            W = Blast.compute_w(deepcopy(W0), Pk)
            Blast.get_Cℓ(ell, used..., Pk, W, bg, plans)
        end
    end
end

npzwrite(request["output"], out)
timings["julia_after_loading"] = time() - t_start
open(request["timings"], "w") do io
    TOML.print(io, timings)
end
'''

BLAST_CHI_MAX = 7000.0  # largest comoving distance of Blast's chi grid (Mpc)


def blast_pad_nz(inputs):
    """The n(z) extended with zeros up to the end of the background table.

    Blast interpolates the n(z) on the redshifts of its chi grid up to
    z(7000 Mpc) ~ 3.5 and extrapolates beyond the last tabulated z instead of
    returning zero: n(z) that do not vanish at the end of the table would get
    spurious tails (biasing the shear by up to ~10%, also in Limber). The
    normalization is unchanged.
    """
    import numpy as np

    z = inputs["z_nz"]
    if inputs["chi"][-1] < BLAST_CHI_MAX:
        raise ValueError(f"The background table ends before Blast's chi_max = {BLAST_CHI_MAX} Mpc: "
                         "raise [tables] z_max.")
    if z[-1] >= np.interp(BLAST_CHI_MAX, inputs["chi"], inputs["z_bg"]):
        return inputs
    dz = z[-1] - z[-2]
    extra = np.arange(1, int(np.ceil((inputs["z_bg"][-1] - z[-1]) / dz)) + 1) * dz + z[-1]
    out = dict(inputs)
    out["z_nz"] = np.concatenate([z, extra])
    for key in ("nz_lens", "nz_source"):
        out[key] = np.concatenate([inputs[key], np.zeros((len(inputs[key]), len(extra)))], axis=1)
    return out


def task_blast(cfg):
    import numpy as np

    project = root(cfg) / "environment" / "blast"
    julia = cfg["environment"].get("julia", "julia")
    with open(project / "Manifest.toml", "rb") as f:
        entry = tomllib.load(f)["deps"]["Blast"][0]
    source = {key: entry.get(key) for key in ("version", "repo-url", "repo-rev", "git-tree-sha1")}
    timings = Timings("blast")
    work = root(cfg) / ".work"
    work.mkdir(exist_ok=True)
    out_dir = data_dir(cfg)
    paths = {k: out_dir / f"blast_{k}" for k in ("inputs.npz", "raw.npz", "timings.toml", "request.toml")}
    script = work / "run_blast.jl"
    with timings("setup/request"):
        script.write_text(BLAST_JL)
        inputs = load_inputs(cfg)
        if cfg.get("codes", {}).get("blast", {}).get("pad_nz_with_zeros", True):
            inputs = blast_pad_nz(inputs)
        np.savez(paths["inputs.npz"], **{k: v for k, v in inputs.items() if v.dtype.kind in "fiu"})
        ia = cfg["intrinsic_alignments"]
        lines = [f'inputs = "{paths["inputs.npz"]}"', f'output = "{paths["raw.npz"]}"',
                 f'timings = "{paths["timings.toml"]}"', f"ells = {[int(l) for l in ells(cfg)]}",
                 f"A_IA = {float(ia['A_IA'])!r}", f"C1_rhocrit = {float(ia['C1_rhocrit'])!r}"]
        for case, (a, b, g_terms, s_terms) in cases(cfg).items():
            lines += [f"[cases.{case}]", f'a = "{a}"', f'b = "{b}"',
                      f"g_terms = {json.dumps(list(g_terms))}", f"s_terms = {json.dumps(list(s_terms))}"]
        paths["request.toml"].write_text("\n".join(lines) + "\n")
    with timings("julia_process"):  # start-up, package loading and JIT included
        subprocess.run([julia, f"--project={project}", str(script), str(paths["request.toml"])], check=True)
    with open(paths["timings.toml"], "rb") as f:
        timings.steps.update(tomllib.load(f))
    with np.load(paths["raw.npz"]) as raw:
        cls = {tuple(key.split("/")): raw[key] for key in raw.files}
    save_cls(cfg, "blast", cls, {"version": source, "ell_limber": 220, "timings": timings.as_dict(),
                                 "t_tildes": "Blast artifact T_tildes_128_64_161"})


# =========================================================================== cosmosis

COSMOSIS_LOAD_INPUTS = r'''
"""cosmosis module: the shared validation inputs in place of camb (written by
nonlimber_validation.py). P(k, z) in h units, distances, growth, n(z), bias
and magnification slope (alpha = 2.5 s). Options: inputs (path), linear (T: the
linear P also as the non-linear one)."""
import numpy as np
from cosmosis.datablock import names, option_section


def setup(options):
    with np.load(options.get_string(option_section, "inputs")) as data:
        inputs = {key: data[key] for key in data.files}
    return inputs, options.get_bool(option_section, "linear", False)


def execute(block, config):
    inputs, linear = config
    h = float(inputs["h"])
    cosmo = names.cosmological_parameters
    block[cosmo, "h0"] = h
    block[cosmo, "omega_m"] = float(inputs["Omega_m"])
    block[cosmo, "omega_b"] = float(inputs["Omega_b"])
    block[cosmo, "omega_c"] = float(inputs["Omega_c"])
    block[cosmo, "omega_k"] = 0.0
    block[cosmo, "omega_lambda"] = 1.0 - float(inputs["Omega_m"])
    z_bg = inputs["z_bg"]
    block[names.distances, "z"] = z_bg
    block[names.distances, "a"] = 1.0 / (1.0 + z_bg)
    block[names.distances, "d_m"] = inputs["chi"]
    block[names.distances, "d_a"] = inputs["chi"] / (1.0 + z_bg)
    block[names.distances, "h"] = inputs["H"] / 299792.458  # 1/Mpc
    block[names.growth_parameters, "z"] = z_bg
    block[names.growth_parameters, "d_z"] = inputs["D"]
    block[names.growth_parameters, "f_z"] = inputs["f"]
    k_h = inputs["k"] / h
    pk_nl = inputs["pk_lin"] if linear else inputs["pk_nl"]
    for section, pk in [(names.matter_power_lin, inputs["pk_lin"]), (names.matter_power_nl, pk_nl)]:
        block.put_grid(section, "z", inputs["z_pk"], "k_h", k_h, "p_k", pk * h**3)
    z = np.concatenate([[0.0], inputs["z_nz"]])  # z = 0 prepended, as the cosmosis loaders do
    for sample, key in [("lens", "nz_lens"), ("source", "nz_source")]:
        nz = inputs[key]
        section = f"nz_{sample}"
        block[section, "nbin"] = len(nz)
        block[section, "nz"] = len(z)
        block[section, "z"] = z
        for i, n in enumerate(nz):
            block[section, f"bin_{i + 1}"] = np.concatenate([[0.0], n])
    for i, (b, s) in enumerate(zip(inputs["bias"], inputs["s"])):
        block["bias_lens", f"b{i + 1}"] = float(b)
        block["mag_alpha_lens", f"alpha_{i + 1}"] = 2.5 * float(s)
    return 0
'''

# project_2d spectrum -> (samples, output section)
COSMOSIS_SPECTRA = {
    "lingal-lingal": ("lens-lens", "galaxy_cl"),
    "lingal-magnification": ("lens-lens", "galaxy_magnification_cl"),
    "magnification-magnification": ("lens-lens", "magnification_cl"),
    "lingal-shear": ("lens-source", "galaxy_shear_cl"),
    "magnification-shear": ("lens-source", "magnification_shear_cl"),
    "fast-lingal-shear-ia": ("lens-source", "galaxy_shear_cl"),
    "shear-shear": ("source-source", "shear_cl"),
    "fast-shear-shear-ia": ("source-source", "shear_cl"),
}


def cosmosis_plan(probe, galaxy, shear):
    """(spectra, with RSD) of a probe, or (None, reason). A spectrum is (name,
    how): "sym" auto stored once per pair, "both" gg cross term in both orders,
    "cross" gs."""
    rsd, mag, ia = "rsd" in galaxy, "magnification" in galaxy, "ia" in shear
    if probe == "gg":
        if rsd and mag:
            return None, "no RSD x magnification in project_2d"
        spectra = [("lingal-lingal", "sym")]
        if mag:
            spectra += [("lingal-magnification", "both"), ("magnification-magnification", "sym")]
        return spectra, rsd
    if probe == "gs":
        if rsd:
            return None, "no galaxy RSD x shear in project_2d"
        if ia:
            if mag:
                return None, "magnification x IA needs an IA power module"
            return [("fast-lingal-shear-ia", "cross")], False
        return [("lingal-shear", "cross")] + ([("magnification-shear", "cross")] if mag else []), False
    return [("fast-shear-shear-ia" if ia else "shear-shear", "sym")], False


def task_cosmosis(cfg):
    import numpy as np
    from cosmosis.runtime.config import Inifile
    from cosmosis.runtime.pipeline import LikelihoodPipeline

    import cosmosis

    csl = resolve(cfg, cfg["environment"]["cosmosis_standard_library"])
    settings = cfg.get("codes", {}).get("cosmosis", {})
    ell_max = int(settings.get("ell_max_linspaced", 1000))
    work = root(cfg) / ".work"
    work.mkdir(exist_ok=True)
    loader = work / "cosmosis_load_inputs.py"
    loader.write_text(COSMOSIS_LOAD_INPUTS)
    # project_2d's IA kernel is A C1 rho_crit with its own C1 rho_crit (its constants).
    c1_m_sun, m_sun, mpc_in_m, g = 5e-14, 1.9891e30, 3.0857e22, 6.67384e-11
    c1_rhocrit_cosmosis = c1_m_sun / m_sun * mpc_in_m**3 * 3 * (1e5 / mpc_in_m) ** 2 / (8 * np.pi * g)
    ia = cfg["intrinsic_alignments"]
    a_ia = ia["A_IA"] * ia["C1_rhocrit"] / c1_rhocrit_cosmosis
    values = work / "cosmosis_values.ini"
    values.write_text(f"[intrinsic_alignment_parameters]\nA = {a_ia!r}\nalpha = 0.0\nz0 = 0.62\n")

    def run(spectra, rsd, exact, linear):
        override = {
            ("runtime", "sampler"): "test", ("pipeline", "modules"): "load_inputs project",
            ("pipeline", "values"): str(values), ("pipeline", "likelihoods"): "",
            ("pipeline", "quiet"): "T", ("pipeline", "timing"): "F", ("pipeline", "debug"): "F",
            ("load_inputs", "file"): str(loader), ("load_inputs", "inputs"): str(inputs_path(cfg)),
            ("load_inputs", "linear"): "T" if linear else "F",
            ("project", "file"): str(csl / "structure" / "projection" / "project_2d.py"),
            ("project", "ell_min_linspaced"): "2", ("project", "ell_max_linspaced"): str(ell_max),
            ("project", "n_ell_linspaced"): str(ell_max - 1), ("project", "fz_from_block"): "T",
            ("project", "verbose"): "F",
            ("project", "chi_pad_lower"): str(float(settings.get("chi_pad_lower", 3.0))),
            ("project", "chi_pad_upper"): str(float(settings.get("chi_pad_upper", 3.0))),
            ("project", "sig_over_dchi_exact"): str(float(settings.get("sig_over_dchi_exact", 20.0))),
        }
        for name in spectra:
            override["project", name] = COSMOSIS_SPECTRA[name][0]
        if exact:
            override["project", "do_exact"] = " ".join(spectra)
            override["project", "limber_ell_start"] = str(int(cfg["ells"]["ell_nonlimber_max"]))
            override["project", "do_rsd"] = "T" if rsd else "F"
        return LikelihoodPipeline(Inifile(None, override=override)).run_parameters([])

    def matrix(block, section, n_a, n_b, symmetric):
        ell = block[section, "ell"]
        out = np.zeros((len(ell), n_a, n_b))
        for i in range(n_a):
            for j in range(n_b):
                key = f"bin_{i + 1}_{j + 1}"
                if symmetric and not block.has_value(section, key):
                    key = f"bin_{j + 1}_{i + 1}"
                out[:, i, j] = block[section, key]
        return ell, out

    ell = ells(cfg)
    lf = ell.astype(float)
    spin2 = np.sqrt((lf + 2) * (lf + 1) * lf * (lf - 1)) / (lf + 0.5) ** 2  # project_2d has no spin-2 factor
    with np.load(inputs_path(cfg)) as data:
        n = {"g": len(data["nz_lens"]), "s": len(data["nz_source"])}
    timings = Timings("cosmosis")
    modes = [("limber", False, False), ("nonlimber", True, False),
             ("limber_lin", False, True), ("nonlimber_lin", True, True)]
    blocks, cls, unsupported = {}, {}, {}
    for case, (a, b, galaxy, shear) in cases(cfg).items():
        spectra, rsd = cosmosis_plan(case.rsplit("__", 1)[1], galaxy, shear)
        if spectra is None:
            unsupported[case] = rsd
            print(f"[cosmosis] {case}: not computed ({rsd})", flush=True)
            continue
        names = tuple(name for name, _ in spectra)
        for mode, exact, linear in modes:
            if rsd and not exact:
                continue  # no Limber RSD in project_2d
            key = (names, rsd, exact, linear)
            if key not in blocks:
                with timings("+".join(names) + ("+rsd" if rsd else "") + f"/{mode}"):
                    blocks[key] = run(names, rsd, exact, linear)
            total = 0.0
            for name, how in spectra:
                ell_c, cl = matrix(blocks[key], COSMOSIS_SPECTRA[name][1], n[a], n[b], how == "sym")
                if how == "both":
                    cl = cl + cl.transpose(0, 2, 1)
                index = np.searchsorted(ell_c, ell)
                if not np.allclose(ell_c[index], ell):
                    raise ValueError("cosmosis ells do not contain the config ells.")
                total = total + cl[index]
            cls[case, mode] = total * spin2[:, None, None] ** ((a == "s") + (b == "s"))
    commit = subprocess.run(["git", "-C", str(csl), "rev-parse", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    save_cls(cfg, "cosmosis", cls, {
        "version": cosmosis.__version__, "standard_library_commit": commit,
        "module": "structure/projection/project_2d.py", "a_ia_passed": a_ia, "unsupported": unsupported,
        "settings": {"limber_ell_start": int(cfg["ells"]["ell_nonlimber_max"]), **settings},
        "timings": timings.as_dict(),
    })


# =========================================================================== plots and tables

STYLE = {
    "cloelib": dict(color="#2a78d6", ls="-"),
    "ccl": dict(color="#eb6834", ls="--"),
    "blast": dict(color="#1baf7a", ls="-."),
    "cosmosis": dict(color="#eda100", ls=(0, (1, 1.5))),
}
MUTED = "#8a8984"
BIN_COLORS = ["#86b6ef", "#2a78d6", "#104281", "#0d366b"]
ARCMIN2_PER_SR = (180 * 60 / 3.141592653589793) ** 2
RANGES = [(2, 10), (11, 60), (61, 200), (201, 1000)]


class Results:
    """The Cl of every code, and the errors of the comparison."""

    def __init__(self, cfg):
        import numpy as np

        self.np = np
        self.cfg = cfg
        self.ells = ells(cfg).astype(float)
        self.cls, self.meta = {}, {}
        for code in CODES:
            try:
                self.cls[code], self.meta[code] = load_cls(cfg, code)
            except FileNotFoundError:
                pass
        with np.load(inputs_path(cfg)) as data:
            self.n = {"g": len(data["nz_lens"]), "s": len(data["nz_source"])}
        p = cfg["plots"]
        self.f_sky, self.ref = p["f_sky"], p["reference"]
        self.noise = {"g": 1.0 / (p["n_gal"] / self.n["g"] * ARCMIN2_PER_SR),
                      "s": p["sigma_e"] ** 2 / (p["n_gal"] / self.n["s"] * ARCMIN2_PER_SR)}

    def get(self, code, setup, probe, mode):
        return self.cls.get(code, {}).get((case_name(setup, probe), mode))

    def codes(self, setup, probe, mode):
        return [c for c in self.cls if self.get(c, setup, probe, mode) is not None]

    def reason(self, code, setup, probe):
        return self.meta.get(code, {}).get("unsupported", {}).get(case_name(setup, probe), "not computed")

    def pairs(self, probe):
        a, b = PROBES[probe]
        if a == b:
            return [(i, j) for i in range(self.n[a]) for j in range(i, self.n[b])]
        return [(i, j) for i in range(self.n[a]) for j in range(self.n[b])]

    def sigma(self, setup, probe, mode, noise=True):
        """Gaussian error of every pair of a probe, from the reference model of the setup."""
        np = self.np
        a, b = PROBES[probe]
        auto = {kind: np.einsum("lii->li", self.get(self.ref, setup, p, mode)) for kind, p in (("g", "gg"), ("s", "ss"))}
        if noise:
            auto = {kind: v + self.noise[kind] for kind, v in auto.items()}
        C = self.get(self.ref, setup, probe, mode).copy()
        if noise and a == b:
            C = C + np.eye(C.shape[1])[None] * self.noise[a]
        var = (auto[a][:, :, None] * auto[b][:, None, :] + C**2) / ((2 * self.ells + 1) * self.f_sky)[:, None, None]
        return np.sqrt(var)

    def delta_chi2(self, setup, mode, code, ell_max, against=None):
        """Delta chi^2 of the 3x2pt of `code` (or `against` = (code, mode)) against
        the reference, every integer ell in [2, ell_max], Knox covariance with
        noise of all the unique spectra; the ell-independent part interpolated in
        log ell between the computed ells <= ell_max (above them every code is in
        its own Limber regime, which must not leak into the sum)."""
        np = self.np

        def fields(c, m):
            parts = [self.get(c, setup, p, m) for p in ("gg", "gs", "ss")]
            if any(x is None for x in parts):
                return None
            gg, gs, ss = parts
            return np.concatenate([np.concatenate([gg, gs], axis=2),
                                   np.concatenate([gs.transpose(0, 2, 1), ss], axis=2)], axis=1)

        C_ref = fields(self.ref, mode)
        C_x = fields(code, mode) if against is None else fields(*against)
        if C_ref is None or C_x is None:
            return float("nan")
        N, n_g = C_ref.shape[1], self.n["g"]
        pairs = [(i, j) for i in range(N) for j in range(i, N)]
        C = C_ref.copy()
        for f in range(N):
            C[:, f, f] += self.noise["g" if f < n_g else "s"]
        delta = C_x - C_ref
        q = np.full(len(self.ells), np.nan)
        for n in range(len(self.ells)):
            d = np.array([delta[n, i, j] for i, j in pairs])
            if np.all(np.isfinite(d)):
                K = np.array([[C[n, i, k] * C[n, j, l] + C[n, i, l] * C[n, j, k] for k, l in pairs]
                              for i, j in pairs])
                q[n] = d @ np.linalg.solve(K, d)
        ok = np.isfinite(q) & (self.ells <= ell_max)
        ell_int = np.arange(2, int(ell_max) + 1)
        q_int = np.interp(np.log(ell_int), np.log(self.ells[ok]), q[ok])
        return float(np.sum((2 * ell_int + 1) * self.f_sky * q_int))


def plotters(cfg, res=None):
    """The figures and tables of a validation. Each plot_* function saves the
    figure to `path`, or returns it when `path` is None (for the notebook)."""
    from types import SimpleNamespace

    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 140, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6, "axes.edgecolor": MUTED,
        "xtick.color": "#52514e", "ytick.color": "#52514e", "lines.linewidth": 1.4,
        "legend.frameon": False, "font.size": 9,
    })
    res = res or Results(cfg)
    ell_nl = cfg["ells"]["ell_nonlimber_max"]

    from matplotlib.lines import Line2D

    def save(fig, path):
        if path is None:
            return fig
        fig.savefig(path)
        plt.close(fig)

    TEXT = "#52514e"
    TERM = {"density": "density", "magnification": "magnification", "rsd": "RSD", "shear": "shear", "ia": "IA (NLA)"}
    MODE_TEXT = {
        "nonlimber": f"non-linear P(k), beyond Limber for $\\ell \\leq {ell_nl}$ and Limber above",
        "nonlimber_lin": f"linear P(k), beyond Limber for $\\ell \\leq {ell_nl}$ and Limber above",
        "limber": "non-linear P(k), Limber at every $\\ell$",
        "limber_lin": "linear P(k), Limber at every $\\ell$",
    }
    survey = (f"$f_{{sky}}$ = {res.f_sky}, {cfg['plots']['n_gal']:g} gal/arcmin$^2$, "
              f"$\\sigma_e$ = {cfg['plots']['sigma_e']}")

    def setup_text(setup):
        """'Setup 5: galaxies = density + magnification + RSD; shear = shear + IA (NLA)'."""
        galaxy, shear = setups(cfg)[setup]
        return (f"Setup {setup.split('_')[0]} ({cfg['name']} bins): galaxies = "
                f"{' + '.join(TERM.get(t, t) for t in galaxy)};  shear = {' + '.join(TERM.get(t, t) for t in shear)}")

    def switch_handle(ls="-"):
        return Line2D([], [], color=MUTED, lw=0.8, ls=ls)

    def switch_label(mode):
        return f"$\\ell$ = {ell_nl}: switch to Limber" if "nonlimber" in mode else f"$\\ell$ = {ell_nl}"

    def head(fig, title, subtitle, handles, labels, legend_title=None):
        """Title, the lines that explain the figure, one legend; then the layout."""
        height, n = fig.get_figheight(), subtitle.count("\n") + 1
        fig.suptitle(title, fontsize=11, fontweight="bold", y=1.0 - 0.10 / height)
        fig.text(0.5, 1.0 - 0.40 / height, subtitle, ha="center", va="top", fontsize=8.5, color=TEXT,
                 linespacing=1.35)
        if handles:
            fig.legend(handles, labels, loc="upper center", ncol=len(handles), fontsize=9, title=legend_title,
                       title_fontsize=8, bbox_to_anchor=(0.5, 1.0 - (0.45 + 0.17 * n) / height))
        extra = 0.2 if legend_title else 0.0
        fig.tight_layout(rect=(0, 0, 1, 1 - (0.9 + 0.17 * n + extra) / height))

    def note(ax, lines):
        """What is missing in a panel, and why (lower right corner)."""
        if lines:
            ax.text(0.98, 0.05, "\n".join(lines), transform=ax.transAxes, ha="right", va="bottom", fontsize=6.5,
                    color=TEXT, bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.0))

    def missing(setup, probe, mode):
        """Notes for the codes without this probe (cosmosis cannot compute some terms)."""
        return [f"{code}: {res.reason(code, setup, probe)}" for code in res.cls
                if res.get(code, setup, probe, mode) is None]

    def not_finite(code, values, what=""):
        """Note for the multipoles where a code returned no finite value."""
        bad = res.ells[~np.isfinite(values)]
        if not bad.size:
            return []
        span = f"{int(bad.min())}" if bad.min() == bad.max() else f"{int(bad.min())}-{int(bad.max())}"
        return [f"{code}: {what}not finite at $\\ell$ = {span}"]

    def pair_grid():
        rows = max(len(res.pairs(p)) for p in PROBES)
        fig, axes = plt.subplots(rows, 3, figsize=(12.5, 1.75 * rows + 1.6), sharex=True, squeeze=False)
        for col, probe in enumerate(PROBES):
            for row in range(len(res.pairs(probe)), rows):
                axes[row, col].set_axis_off()
            axes[0, col].set_title(f"{TITLES[probe]} ({probe})", fontsize=10)
        return fig, axes

    def label_pair(ax, probe, i, j):
        a, b = PROBES[probe]
        ax.text(0.02, 0.88, f"{a}{i + 1} x {b}{j + 1}", transform=ax.transAxes, fontsize=8, color=TEXT,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.0))

    def finish(fig, axes, title, subtitle, path, ylabel, extra=()):
        for col, probe in enumerate(PROBES):
            last = axes[len(res.pairs(probe)) - 1, col]
            last.set_xlabel(r"multipole $\ell$")
            last.tick_params(labelbottom=True)
        for ax in axes[:, 0]:
            ax.set_ylabel(ylabel, fontsize=8)
        handles = {}
        for ax in axes.flat:
            for h, lab in zip(*ax.get_legend_handles_labels()):
                handles.setdefault(lab, h)
        for h, lab in extra:
            handles[lab] = h
        head(fig, title, subtitle, list(handles.values()), list(handles))
        return save(fig, path)

    def symlog(ax, values):
        top = np.nanmax(np.abs(values))
        linthresh = top * 1e-3
        ax.set_yscale("symlog", linthresh=linthresh)
        decades = 10.0 ** np.arange(np.floor(np.log10(linthresh)) + 1, np.ceil(np.log10(top)) + 1)
        decades = decades[::max(1, len(decades) // 2)]
        ax.set_yticks(np.concatenate([-decades[::-1], [0.0], decades]))
        ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())

    def plot_cl(setup, mode, path):
        fig, axes = pair_grid()
        pref = res.ells * (res.ells + 1) / (2 * np.pi)
        limber = mode.replace("nonlimber", "limber")
        for col, probe in enumerate(PROBES):
            for row, (i, j) in enumerate(res.pairs(probe)):
                ax = axes[row, col]
                notes = missing(setup, probe, mode) if row == 0 else []
                for code in res.codes(setup, probe, mode):
                    values = res.get(code, setup, probe, mode)[:, i, j]
                    ax.plot(res.ells, pref * values, label=code, **STYLE[code])
                    notes += not_finite(code, values)
                lim = res.get(res.ref, setup, probe, limber)
                if limber != mode and lim is not None:
                    ax.plot(res.ells, pref * lim[:, i, j], color="#3d3c39", ls=(0, (4, 2)), lw=0.9,
                            label=f"{res.ref}, Limber at every $\\ell$")
                values = pref * res.get(res.ref, setup, probe, mode)[:, i, j]
                symlog(ax, values) if np.nanmin(values) < 0 else ax.set_yscale("log")
                ax.set_xscale("log")
                ax.axvline(ell_nl, color=MUTED, lw=0.8)
                label_pair(ax, probe, i, j)
                note(ax, notes)
        subtitle = (f"Angular power spectra of every pair of bins, all codes: {MODE_TEXT[mode]}.\n"
                    "The codes are meant to overlap (their differences are in the delta_sigma and maer figures); "
                    "the Limber-only curve shows where the beyond-Limber correction matters.")
        return finish(fig, axes, setup_text(setup), subtitle, path, r"$\ell(\ell+1)C_\ell/2\pi$",
               extra=[(switch_handle(), switch_label(mode))])

    def plot_delta_sigma(setup, mode, path):
        fig, axes = pair_grid()
        curves, top = [], 0.0
        for col, probe in enumerate(PROBES):
            ref = res.get(res.ref, setup, probe, mode)
            if ref is None:
                continue
            sigma = res.sigma(setup, probe, mode)
            for row, (i, j) in enumerate(res.pairs(probe)):
                ax = axes[row, col]
                notes = missing(setup, probe, mode) if row == 0 else []
                for code in res.codes(setup, probe, mode):
                    if code != res.ref:
                        d = (res.get(code, setup, probe, mode) - ref)[:, i, j] / sigma[:, i, j]
                        ax.plot(res.ells, d, label=code, **STYLE[code])
                        notes += not_finite(code, d)
                        top = max(top, np.nanmax(np.abs(d), initial=0.0))
                curves.append(ax)
                label_pair(ax, probe, i, j)
                note(ax, notes)
        # One axis for every panel: linear within +-1e-3, logarithmic outside.
        limit = max(1.0, 3.0 * top)  # room for the labels above and below +-0.1
        ticks = [t for t in (1e-3, 1e-2, 1e-1, 1.0, 10.0) if t < limit]
        for ax in curves:
            ax.axhline(0, color=MUTED, lw=0.8)
            for y in (-0.1, 0.1):
                ax.axhline(y, color=MUTED, lw=0.7, ls=":")
            ax.set_xscale("log")
            ax.set_yscale("symlog", linthresh=1e-3)
            ax.set_ylim(-limit, limit)
            ax.set_yticks([-t for t in ticks[::-1]] + [0.0] + ticks)
            ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
            ax.tick_params(axis="y", labelsize=7)
            ax.axvline(ell_nl, color=MUTED, lw=0.8)
        subtitle = (f"Difference of each code from {res.ref}, in units of the statistical error of that spectrum "
                    f"(Gaussian, with noise: {survey}); {MODE_TEXT[mode]}.\n"
                    "Same vertical axis in every panel: linear within $\\pm10^{-3}$, logarithmic outside.")
        return finish(fig, axes, setup_text(setup), subtitle, path,
               f"$(C_\\ell^{{code}} - C_\\ell^{{{res.ref}}}) / \\sigma_\\ell$",
               extra=[(switch_handle(":"), r"$\pm 0.1\,\sigma$"), (switch_handle(), switch_label(mode))])

    def plot_maer(setup, mode, path):
        codes = [c for c in res.cls if c != res.ref]
        if not codes:
            return
        fig, axes = plt.subplots(len(codes), 3, figsize=(12.5, 2.8 * len(codes) + 1.9), sharex=True, sharey=True,
                                 squeeze=False)
        handles, top = [], 0.0
        for row, code in enumerate(codes):
            for col, probe in enumerate(PROBES):
                ax = axes[row, col]
                x, ref = res.get(code, setup, probe, mode), res.get(res.ref, setup, probe, mode)
                if x is None or ref is None:
                    ax.text(0.5, 0.5, f"{code}: {res.reason(code, setup, probe)}", ha="center", va="center",
                            fontsize=8, color=TEXT, transform=ax.transAxes)
                else:
                    sigma = res.sigma(setup, probe, mode, noise=False)
                    d = 100 * np.abs(np.einsum("lii->li", x - ref)) / np.einsum("lii->li", sigma)
                    notes = []
                    for i in range(d.shape[1]):
                        ax.plot(res.ells, d[:, i], color=BIN_COLORS[i % len(BIN_COLORS)], label=f"bin {i + 1}")
                        notes += not_finite(code, d[:, i], f"bin {i + 1} ")
                    top = max(top, np.nanmax(d, initial=0.0))
                    ax.axvline(ell_nl, color=MUTED, lw=0.8)
                    if code == "blast":
                        ax.axvline(220, color=MUTED, lw=0.8, ls=":")
                    note(ax, notes)
                    handles = handles or ax.get_legend_handles_labels()[0]
                ax.set_xscale("log")
                ax.tick_params(labelleft=True)
                if row == 0:
                    ax.set_title(f"{TITLES[probe]} ({probe})", fontsize=10)
                if col == 0:
                    ax.set_ylabel(f"{code} vs {res.ref}\n" + r"$100\,|\Delta C_\ell| / \sigma^{CV}_\ell$ [%]", fontsize=8)
                if row == len(codes) - 1:
                    ax.set_xlabel(r"multipole $\ell$")
        axes[0, 0].set_yscale("log")
        axes[0, 0].set_ylim(1e-3, max(1.0, 3.0 * top))
        labels = [h.get_label() for h in handles] + [switch_label(mode)]
        handles = list(handles) + [switch_handle()]
        if "blast" in codes:
            handles.append(switch_handle(":"))
            labels.append(r"$\ell$ = 220: Blast's own switch to Limber")
        subtitle = (f"Absolute difference of each code (one row each) from {res.ref}, in percent of the "
                    f"cosmic-variance error (no noise, $f_{{sky}}$ = {res.f_sky}); {MODE_TEXT[mode]}.\n"
                    "Only the spectra of a bin with itself (g$_i$ x g$_i$, g$_i$ x s$_i$, s$_i$ x s$_i$). "
                    "Same logarithmic axis in every panel (differences below $10^{-3}$ % are off the axis).\n"
                    "The step at the switch is the change of method (every code joins its own Limber there), "
                    "not a difference of the beyond-Limber calculation.")
        head(fig, setup_text(setup), subtitle, handles, labels)
        return save(fig, path)

    def tables(setup, mode):
        lines = [f"### {mode}", "", f"Maximum |C_code - C_{res.ref}| / sigma_ij over all bin pairs "
                 f"(Gaussian error with noise, f_sky = {res.f_sky}):", "",
                 "| probe | code | " + " | ".join(f"l {lo}-{hi}" for lo, hi in RANGES) + " |",
                 "|---|---|" + "---|" * len(RANGES)]
        for probe in PROBES:
            ref = res.get(res.ref, setup, probe, mode)
            if ref is None:
                continue
            sigma = res.sigma(setup, probe, mode)
            for code in res.cls:
                if code == res.ref:
                    continue
                x = res.get(code, setup, probe, mode)
                if x is None:
                    lines.append(f"| {probe} | {code} | {res.reason(code, setup, probe)} |" + " |" * (len(RANGES) - 1))
                    continue
                d, cells = np.abs(x - ref) / sigma, []
                for lo, hi in RANGES:
                    v = d[(res.ells >= lo) & (res.ells <= hi)]
                    v = v[np.isfinite(v)]
                    cells.append(f"{v.max():.1e}" if v.size else "-")
                lines.append(f"| {probe} | {code} | " + " | ".join(cells) + " |")
        top = int(res.ells.max())
        lines += ["", f"Delta chi^2 of the 3x2pt against {res.ref} (Knox, with noise, f_sky = {res.f_sky}):", "",
                  f"| code | l <= {int(ell_nl)} | l <= {top} |", "|---|---|---|"]
        for code in [c for c in res.cls if c != res.ref] + ["(Limber)"]:
            if code == "(Limber)":
                limber = mode.replace("nonlimber", "limber")
                if limber == mode:
                    continue
                row = [res.delta_chi2(setup, mode, None, L, against=(res.ref, limber)) for L in (ell_nl, top)]
                name = f"{res.ref} Limber (size of the correction)"
            else:
                row, name = [res.delta_chi2(setup, mode, code, L) for L in (ell_nl, top)], code
            lines.append(f"| {name} | " + " | ".join("-" if v != v else f"{v:.3g}" for v in row) + " |")
        return lines + [""]

    return SimpleNamespace(res=res, plot_cl=plot_cl, plot_delta_sigma=plot_delta_sigma, plot_maer=plot_maer,
                           tables=tables)


def task_plots(cfg):
    import matplotlib

    matplotlib.use("Agg")

    p = plotters(cfg)
    res = p.res
    plot_cl, plot_delta_sigma, plot_maer, tables = p.plot_cl, p.plot_delta_sigma, p.plot_maer, p.tables
    out = root(cfg) / "results" / cfg["name"]
    overall = [f"# Validation: {cfg['name']}", "", f"Codes: {', '.join(res.cls)}; reference: {res.ref}.", ""]
    for setup in setups(cfg):
        folder = out / setup
        folder.mkdir(parents=True, exist_ok=True)
        text = [f"# {setup}", ""]
        for mode in cfg["plots"]["modes"]:
            plot_cl(setup, mode, folder / f"cl__{mode}.png")
            plot_delta_sigma(setup, mode, folder / f"delta_sigma__{mode}.png")
            plot_maer(setup, mode, folder / f"maer__{mode}.png")
            text += tables(setup, mode)
        (folder / "summary.md").write_text("\n".join(text))
        overall += [f"## {setup}", ""] + text[2:]
        print(f"[plots] results/{cfg['name']}/{setup}/", flush=True)
    overall += ["## Versions and provenance", "", "| code | version | provenance |", "|---|---|---|"]
    for code, meta in res.meta.items():
        overall.append(f"| {code} | `{json.dumps(meta.get('version'))}` | `{json.dumps(meta.get('provenance', {}))}` |")
    (out / "summary.md").write_text("\n".join(overall) + "\n")


TASKS = {"inputs": task_inputs, "cloelib": task_cloelib, "ccl": task_ccl, "blast": task_blast,
         "cosmosis": task_cosmosis, "plots": task_plots}
# The environment each task runs in.
TASK_ENV = {"inputs": "cloelib", "cloelib": "cloelib", "blast": "cloelib", "plots": "cloelib",
            "ccl": "ccl", "cosmosis": "cosmosis"}


# =========================================================================== environments


def conda_executable(cfg):
    exe = cfg["environment"].get("conda", "auto")
    if exe != "auto":
        return os.path.expanduser(exe)
    for candidate in (os.environ.get("CONDA_EXE"), os.environ.get("MAMBA_EXE"),
                      shutil.which("conda"), shutil.which("mamba"), shutil.which("micromamba")):
        if candidate:
            return candidate
    raise RuntimeError("No conda, mamba or micromamba found: set [environment] conda in local.toml.")


def in_env(cfg, env, command):
    """A bash command running `command` (a string) in the environment `env`."""
    spec = cfg["environment"][env]
    prefix = "source cosmosis-configure > /dev/null && " if env == "cosmosis" else ""
    if "python" in spec:
        python = str(resolve(cfg, spec["python"]))  # relative to the config; symlinks kept (venvs)
        bindir = shlex.quote(str(Path(python).parent))
        return f"PATH={bindir}:$PATH {prefix}{command.replace('python ', shlex.quote(python) + ' ', 1)}"
    conda = conda_executable(cfg)
    capture = "" if Path(conda).name.startswith("micromamba") else "--no-capture-output "
    return f"{shlex.quote(conda)} run {capture}-n {shlex.quote(spec['conda'])} bash -c {shlex.quote(prefix + command)}"


def run_task(cfg, task):
    logs = root(cfg) / "logs" / cfg["name"]
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"{task}.log"
    command = in_env(cfg, TASK_ENV[task], f"python {shlex.quote(str(SCRIPT))} worker {task} "
                                          f"{shlex.quote(cfg['_path'])}")
    print(f"[validation] {task} ...", flush=True)
    with open(log, "w") as f:
        result = subprocess.run(["bash", "-c", command], cwd=root(cfg), stdout=f, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        tail = "\n".join(log.read_text().splitlines()[-25:])
        raise SystemExit(f"[validation] {task} failed (log: {log}):\n{tail}")
    print(f"[validation] {task}: done (log: {log})", flush=True)


# =========================================================================== setup


def setup(cfg, dry_run=False, force=False):
    """Create the environments, install cloelib, clone the cosmosis standard
    library, instantiate the Julia project of Blast."""
    env_dir = root(cfg) / "environment"
    steps = []

    def step(description, command):
        steps.append((description, command))

    needs_conda = any("conda" in cfg["environment"][e] for e in ("cloelib", "ccl", "cosmosis"))
    conda = conda_executable(cfg) if needs_conda else None
    existing = set()
    if conda:
        listing = subprocess.run([conda, "env", "list", "--json"], capture_output=True, text=True)
        existing = {Path(p).name for p in json.loads(listing.stdout or "{}").get("envs", [])}
    for env, yml in (("cloelib", "cloelib.yml"), ("ccl", "ccl.yml"), ("cosmosis", "cosmosis.yml")):
        spec = cfg["environment"][env]
        if "conda" not in spec:
            print(f"[setup] {env}: using {spec['python']} (not created)")
            continue
        name = spec["conda"]
        if name in existing and not force:
            print(f"[setup] {env}: conda env {name!r} exists (--force to update it)")
            continue
        action = "update" if name in existing else "create"
        step(f"{action} conda env {name}", f"{shlex.quote(conda)} env {action} -n {shlex.quote(name)} "
                                           f"-f {shlex.quote(str(env_dir / yml))}")
    # cloelib only into an environment `setup` manages, and not when a local
    # source tree is used ([environment] cloelib_path).
    if cfg["environment"].get("cloelib_path"):
        print(f"[setup] cloelib: imported from {resolve(cfg, cfg['environment']['cloelib_path'])} (not installed)")
    elif "conda" not in cfg["environment"]["cloelib"]:
        print("[setup] cloelib: your own environment, install it there yourself: "
              f"pip install {cfg['setup']['cloelib']}")
    else:
        step("install cloelib (" + cfg["setup"]["cloelib"] + ")",
             in_env(cfg, "cloelib", f"python -m pip install {shlex.quote(cfg['setup']['cloelib'])}"))
    csl = resolve(cfg, cfg["environment"]["cosmosis_standard_library"])
    url, commit = cfg["setup"]["cosmosis_standard_library_url"], cfg["setup"]["cosmosis_standard_library_commit"]
    if not (csl / ".git").exists():
        step(f"clone the cosmosis standard library at {commit[:8]}",
             f"mkdir -p {shlex.quote(str(csl))} && cd {shlex.quote(str(csl))} && git init -q && "
             f"git remote add origin {shlex.quote(url)} && git fetch -q --depth 1 origin {commit} && "
             "git checkout -q FETCH_HEAD")
    else:
        print(f"[setup] cosmosis standard library: {csl} exists")
    julia = cfg["environment"].get("julia", "julia")
    if not shutil.which(os.path.expanduser(julia)) and not dry_run:
        raise SystemExit(f"[setup] Julia ({julia!r}) not found: install Julia >= 1.10 (e.g. juliaup) "
                         "or set [environment] julia in local.toml.")
    step("instantiate the Julia project of Blast",
         f"{shlex.quote(julia)} --project={shlex.quote(str(env_dir / 'blast'))} -e 'using Pkg; Pkg.instantiate()'")
    for description, command in steps:
        print(f"[setup] {description}\n        $ {command}", flush=True)
        if not dry_run:
            subprocess.run(["bash", "-c", command], check=True)
    if not dry_run:
        print("[setup] done. The T-tilde dataset (1.8 GB) is downloaded by cloelib on the first run.")


# =========================================================================== main


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("setup", help="create the environments")
    p.add_argument("--dry-run", action="store_true", help="only print the commands")
    p.add_argument("--force", action="store_true", help="update existing environments")
    p = sub.add_parser("run", help="inputs (if missing), the codes, the plots")
    p.add_argument("--codes", nargs="+", choices=CODES, help="codes to run (default: `run` of the config)")
    p.add_argument("--inputs", action="store_true", help="recompute the shared inputs")
    sub.add_parser("plots", help="only plots and tables")
    p = sub.add_parser("worker", help=argparse.SUPPRESS)
    p.add_argument("task", choices=list(TASKS))
    for p in sub.choices.values():
        p.add_argument("config", nargs="?", default=str(SCRIPT.parent / "config.toml"))
    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.command == "worker":
        TASKS[args.task](cfg)
    elif args.command == "setup":
        setup(cfg, args.dry_run, args.force)
    elif args.command == "plots":
        run_task(cfg, "plots")
    else:
        if args.inputs or not inputs_path(cfg).exists():
            run_task(cfg, "inputs")
        for code in args.codes or cfg["run"]:
            run_task(cfg, code)
        run_task(cfg, "plots")


if __name__ == "__main__":
    main()
