# Validation: gaussian

Codes: cloelib, ccl, blast, cosmosis; reference: cloelib.

## 1_density_x_shear

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 2.3e-03 | 1.9e-03 | 6.3e-03 | 3.5e-04 |
| gg | blast | 9.9e-03 | 2.9e-03 | 3.4e-03 | 1.4e-02 |
| gg | cosmosis | 6.7e-04 | 1.3e-03 | 4.1e-03 | 1.7e-04 |
| gs | ccl | 3.0e-03 | 6.7e-04 | 2.2e-03 | 2.6e-04 |
| gs | blast | 9.2e-04 | 7.1e-04 | 1.7e-03 | 4.6e-03 |
| gs | cosmosis | 1.7e-01 | 5.9e-02 | 1.2e-02 | 1.8e-05 |
| ss | ccl | 6.1e-03 | 2.7e-03 | 2.9e-03 | 8.5e-05 |
| ss | blast | 3.9e-03 | 6.9e-03 | 3.4e-03 | 1.4e-03 |
| ss | cosmosis | 1.6e-01 | 4.1e-02 | 4.0e-03 | 5.8e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.0106 | 0.0106 |
| blast | 0.00313 | 0.0182 |
| cosmosis | 3.64 | 3.64 |
| cloelib Limber (size of the correction) | 10.2 | 10.2 |

## 2_density-magnification_x_shear

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 2.4e-03 | 1.9e-03 | 6.3e-03 | 3.6e-04 |
| gg | blast | 9.7e-03 | 2.9e-03 | 3.4e-03 | 1.4e-02 |
| gg | cosmosis | 8.9e-03 | 5.6e-03 | 4.2e-03 | 1.7e-04 |
| gs | ccl | 3.0e-03 | 6.7e-04 | 2.2e-03 | 2.6e-04 |
| gs | blast | 1.0e-03 | 7.2e-04 | 1.7e-03 | 4.6e-03 |
| gs | cosmosis | 1.7e-01 | 5.9e-02 | 1.2e-02 | 1.8e-05 |
| ss | ccl | 6.1e-03 | 2.7e-03 | 2.9e-03 | 8.5e-05 |
| ss | blast | 3.9e-03 | 6.9e-03 | 3.4e-03 | 1.4e-03 |
| ss | cosmosis | 1.6e-01 | 4.1e-02 | 4.0e-03 | 5.8e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.0106 | 0.0106 |
| blast | 0.00313 | 0.0182 |
| cosmosis | 3.63 | 3.63 |
| cloelib Limber (size of the correction) | 10.2 | 10.2 |

## 3_density-rsd_x_shear

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 1.3e-03 | 2.7e-03 | 1.0e-02 | 3.4e-02 |
| gg | blast | 5.0e-03 | 1.9e-03 | 4.5e-03 | 2.8e-02 |
| gg | cosmosis | 9.6e-04 | 1.8e-03 | 7.7e-03 | 3.4e-02 |
| gs | ccl | 2.1e-03 | 6.5e-04 | 2.3e-03 | 7.1e-04 |
| gs | blast | 5.4e-04 | 8.6e-04 | 1.8e-03 | 4.7e-03 |
| gs | cosmosis | no galaxy RSD x shear in project_2d | | | |
| ss | ccl | 6.1e-03 | 2.7e-03 | 2.9e-03 | 8.5e-05 |
| ss | blast | 3.9e-03 | 6.9e-03 | 3.4e-03 | 1.4e-03 |
| ss | cosmosis | 1.6e-01 | 4.1e-02 | 4.0e-03 | 5.8e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.0147 | 0.192 |
| blast | 0.0034 | 0.15 |
| cosmosis | - | - |
| cloelib Limber (size of the correction) | 9.62 | 9.62 |

## 4_density_x_shear-ia

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 2.3e-03 | 1.9e-03 | 6.3e-03 | 3.5e-04 |
| gg | blast | 9.9e-03 | 2.9e-03 | 3.4e-03 | 1.4e-02 |
| gg | cosmosis | 6.7e-04 | 1.3e-03 | 4.1e-03 | 1.7e-04 |
| gs | ccl | 2.9e-03 | 1.2e-03 | 2.3e-03 | 2.6e-04 |
| gs | blast | 2.3e-03 | 7.3e-04 | 1.7e-03 | 1.1e-02 |
| gs | cosmosis | 3.1e-01 | 1.4e-01 | 2.7e-02 | 1.7e-04 |
| ss | ccl | 6.5e-03 | 3.2e-03 | 1.9e-03 | 3.9e-05 |
| ss | blast | 4.4e-03 | 7.3e-03 | 3.1e-03 | 1.5e-03 |
| ss | cosmosis | 1.8e-01 | 5.4e-02 | 7.1e-03 | 8.3e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.00519 | 0.00514 |
| blast | 0.00336 | 0.0238 |
| cosmosis | 11.9 | 11.9 |
| cloelib Limber (size of the correction) | 16.6 | 16.6 |

## 5_density-magnification-rsd_x_shear-ia

### nonlimber

Maximum |C_code - C_cloelib| / sigma_ij over all bin pairs (Gaussian error with noise, f_sky = 0.36):

| probe | code | l 2-10 | l 11-60 | l 61-200 | l 201-1000 |
|---|---|---|---|---|---|
| gg | ccl | 1.4e-03 | 2.6e-03 | 1.0e-02 | 3.4e-02 |
| gg | blast | 5.1e-03 | 1.9e-03 | 4.5e-03 | 2.7e-02 |
| gg | cosmosis | no RSD x magnification in project_2d | | | |
| gs | ccl | 1.1e-03 | 1.2e-03 | 2.3e-03 | 2.6e-03 |
| gs | blast | 1.3e-03 | 8.8e-04 | 1.8e-03 | 1.1e-02 |
| gs | cosmosis | no galaxy RSD x shear in project_2d | | | |
| ss | ccl | 6.5e-03 | 3.2e-03 | 1.9e-03 | 3.9e-05 |
| ss | blast | 4.4e-03 | 7.3e-03 | 3.1e-03 | 1.5e-03 |
| ss | cosmosis | 1.8e-01 | 5.4e-02 | 7.1e-03 | 8.3e-05 |

Delta chi^2 of the 3x2pt against cloelib (Knox, with noise, f_sky = 0.36):

| code | l <= 200 | l <= 1000 |
|---|---|---|
| ccl | 0.00925 | 0.185 |
| blast | 0.00355 | 0.156 |
| cosmosis | - | - |
| cloelib Limber (size of the correction) | 15.3 | 15.3 |

## Versions and provenance

| code | version | provenance |
|---|---|---|
| cloelib | `{"path": "~/documents/phd_2025/cloe_beyondL/cloelib/cloelib", "version": null, "commit": "f7bfbdccf95172ab4fe29073f37f6a7c94a7549e", "branch": "feature/no-limber", "dirty": false}` | `{"date": "2026-11-12T18:18:48+00:00", "host": "archlinux", "python": "3.12.13", "script_sha256": "5da227786b488bf377ef669b7c4e2f399eec3bfdce8289707833c9dbfe126bff", "inputs_sha256": "c714a54ca8149ba4ccabc79d96c86b392c3212d8483a688164e447ebd859ae62"}` |
| ccl | `"3.3.6"` | `{"date": "2026-11-12T18:19:35+00:00", "host": "archlinux", "python": "3.13.16", "script_sha256": "5da227786b488bf377ef669b7c4e2f399eec3bfdce8289707833c9dbfe126bff", "inputs_sha256": "c714a54ca8149ba4ccabc79d96c86b392c3212d8483a688164e447ebd859ae62"}` |
| blast | `{"version": "0.1.0", "repo-url": "https://github.com/sofiachiarenza/Blast.jl", "repo-rev": "main", "git-tree-sha1": "b02beff085914f8a7b4ea910d59ef55a862db9ad"}` | `{"date": "2026-11-12T18:21:26+00:00", "host": "archlinux", "python": "3.12.13", "script_sha256": "5da227786b488bf377ef669b7c4e2f399eec3bfdce8289707833c9dbfe126bff", "inputs_sha256": "c714a54ca8149ba4ccabc79d96c86b392c3212d8483a688164e447ebd859ae62"}` |
| cosmosis | `"3.26"` | `{"date": "2026-11-12T18:24:16+00:00", "host": "archlinux", "python": "3.12.15", "script_sha256": "5da227786b488bf377ef669b7c4e2f399eec3bfdce8289707833c9dbfe126bff", "inputs_sha256": "c714a54ca8149ba4ccabc79d96c86b392c3212d8483a688164e447ebd859ae62"}` |
