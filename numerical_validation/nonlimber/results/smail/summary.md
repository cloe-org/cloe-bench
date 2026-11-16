# Validation: smail

Codes: cloelib, ccl, blast, cosmosis; reference: cloelib.

## 1_density_x_shear

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 3.9e-03 | 1.3e-03 | 2.3e-03 | 5.7e-04 |
| gg | blast | 2.9e-03 | 7.5e-04 | 1.5e-03 | 6.1e-03 |
| gg | cosmosis | 2.4e-04 | 1.9e-04 | 1.3e-03 | 3.7e-05 |
| gs | ccl | 4.7e-03 | 2.9e-04 | 1.5e-03 | 2.0e-04 |
| gs | blast | 5.9e-04 | 3.1e-04 | 9.6e-04 | 2.8e-03 |
| gs | cosmosis | 1.4e-01 | 4.9e-02 | 8.5e-03 | 1.1e-05 |
| ss | ccl | 4.3e-03 | 1.3e-03 | 8.4e-04 | 6.8e-05 |
| ss | blast | 2.0e-03 | 2.9e-03 | 1.3e-03 | 1.9e-03 |
| ss | cosmosis | 1.3e-01 | 2.9e-02 | 4.1e-03 | 4.6e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.00198 | 0.00252 |
| blast | 0.00174 | 0.0118 |
| cosmosis | 4.29 | 4.29 |
| cloelib Limber (size of the correction) | 6.1 | 6.1 |

## 2_density-magnification_x_shear

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 4.5e-03 | 1.3e-03 | 2.3e-03 | 5.7e-04 |
| gg | blast | 2.8e-03 | 7.1e-04 | 1.5e-03 | 5.8e-03 |
| gg | cosmosis | 1.7e-02 | 5.6e-03 | 1.2e-03 | 3.7e-05 |
| gs | ccl | 4.6e-03 | 2.9e-04 | 1.5e-03 | 2.0e-04 |
| gs | blast | 7.0e-04 | 3.2e-04 | 9.6e-04 | 2.8e-03 |
| gs | cosmosis | 1.4e-01 | 4.9e-02 | 8.5e-03 | 1.1e-05 |
| ss | ccl | 4.3e-03 | 1.3e-03 | 8.4e-04 | 6.8e-05 |
| ss | blast | 2.0e-03 | 2.9e-03 | 1.3e-03 | 1.9e-03 |
| ss | cosmosis | 1.3e-01 | 2.9e-02 | 4.1e-03 | 4.6e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.00196 | 0.0025 |
| blast | 0.00174 | 0.0118 |
| cosmosis | 4.22 | 4.22 |
| cloelib Limber (size of the correction) | 6.08 | 6.07 |

## 3_density-rsd_x_shear

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 9.8e-04 | 8.7e-04 | 2.6e-03 | 6.4e-03 |
| gg | blast | 6.3e-04 | 2.6e-04 | 1.2e-03 | 5.8e-03 |
| gg | cosmosis | 4.1e-04 | 2.2e-04 | 1.6e-03 | 6.8e-03 |
| gs | ccl | 2.0e-03 | 2.8e-04 | 1.4e-03 | 4.4e-04 |
| gs | blast | 5.1e-04 | 3.0e-04 | 9.5e-04 | 2.9e-03 |
| gs | cosmosis | no galaxy RSD x shear in project_2d | | | |
| ss | ccl | 4.3e-03 | 1.3e-03 | 8.4e-04 | 6.8e-05 |
| ss | blast | 2.0e-03 | 2.9e-03 | 1.3e-03 | 1.9e-03 |
| ss | cosmosis | 1.3e-01 | 2.9e-02 | 4.1e-03 | 4.6e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.00097 | 0.0251 |
| blast | 0.00165 | 0.0298 |
| cosmosis | - | - |
| cloelib Limber (size of the correction) | 5.83 | 5.83 |

## 4_density_x_shear-ia

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 3.9e-03 | 1.3e-03 | 2.3e-03 | 5.7e-04 |
| gg | blast | 2.9e-03 | 7.5e-04 | 1.5e-03 | 6.1e-03 |
| gg | cosmosis | 2.4e-04 | 1.9e-04 | 1.3e-03 | 3.7e-05 |
| gs | ccl | 4.5e-03 | 2.9e-04 | 1.5e-03 | 7.0e-05 |
| gs | blast | 7.8e-04 | 3.1e-04 | 9.6e-04 | 4.0e-03 |
| gs | cosmosis | 1.6e-01 | 7.0e-02 | 1.3e-02 | 9.6e-05 |
| ss | ccl | 4.6e-03 | 1.5e-03 | 9.7e-04 | 2.3e-05 |
| ss | blast | 2.2e-03 | 3.4e-03 | 1.6e-03 | 1.9e-03 |
| ss | cosmosis | 1.3e-01 | 3.2e-02 | 4.4e-03 | 6.9e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.00191 | 0.00244 |
| blast | 0.00181 | 0.0127 |
| cosmosis | 9.48 | 9.48 |
| cloelib Limber (size of the correction) | 9.94 | 9.94 |

## 5_density-magnification-rsd_x_shear-ia

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 9.8e-04 | 8.6e-04 | 2.6e-03 | 6.2e-03 |
| gg | blast | 6.3e-04 | 2.6e-04 | 1.2e-03 | 5.7e-03 |
| gg | cosmosis | no RSD x magnification in project_2d | | | |
| gs | ccl | 1.6e-03 | 2.8e-04 | 1.5e-03 | 6.1e-04 |
| gs | blast | 6.5e-04 | 3.1e-04 | 9.6e-04 | 4.1e-03 |
| gs | cosmosis | no galaxy RSD x shear in project_2d | | | |
| ss | ccl | 4.6e-03 | 1.5e-03 | 9.7e-04 | 2.3e-05 |
| ss | blast | 2.2e-03 | 3.4e-03 | 1.6e-03 | 1.9e-03 |
| ss | cosmosis | 1.3e-01 | 3.2e-02 | 4.4e-03 | 6.9e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.000985 | 0.0259 |
| blast | 0.00172 | 0.0315 |
| cosmosis | - | - |
| cloelib Limber (size of the correction) | 9.75 | 9.75 |

## Versions and provenance

| code | version | provenance |
|---|---|---|
| cloelib | `{"path": "~/documents/phd_2025/cloe_beyondL/cloelib/cloelib", "version": null, "commit": "f7bfbdccf95172ab4fe29073f37f6a7c94a7549e", "branch": "feature/no-limber", "dirty": false}` | `{"date": "2026-11-12T18:25:22+00:00", "host": "archlinux", "python": "3.12.13", "script_sha256": "5da227786b488bf377ef669b7c4e2f399eec3bfdce8289707833c9dbfe126bff", "inputs_sha256": "d196cc79cefe9774c7a6fda43a6e1d13392d80389ffb149005bae24c3d1f95b3"}` |
| ccl | `"3.3.6"` | `{"date": "2026-11-12T18:26:11+00:00", "host": "archlinux", "python": "3.13.16", "script_sha256": "5da227786b488bf377ef669b7c4e2f399eec3bfdce8289707833c9dbfe126bff", "inputs_sha256": "d196cc79cefe9774c7a6fda43a6e1d13392d80389ffb149005bae24c3d1f95b3"}` |
| blast | `{"version": "0.1.0", "repo-url": "https://github.com/sofiachiarenza/Blast.jl", "repo-rev": "main", "git-tree-sha1": "b02beff085914f8a7b4ea910d59ef55a862db9ad"}` | `{"date": "2026-11-12T18:27:55+00:00", "host": "archlinux", "python": "3.12.13", "script_sha256": "5da227786b488bf377ef669b7c4e2f399eec3bfdce8289707833c9dbfe126bff", "inputs_sha256": "d196cc79cefe9774c7a6fda43a6e1d13392d80389ffb149005bae24c3d1f95b3"}` |
| cosmosis | `"3.26"` | `{"date": "2026-11-12T18:30:20+00:00", "host": "archlinux", "python": "3.12.15", "script_sha256": "5da227786b488bf377ef669b7c4e2f399eec3bfdce8289707833c9dbfe126bff", "inputs_sha256": "d196cc79cefe9774c7a6fda43a6e1d13392d80389ffb149005bae24c3d1f95b3"}` |
