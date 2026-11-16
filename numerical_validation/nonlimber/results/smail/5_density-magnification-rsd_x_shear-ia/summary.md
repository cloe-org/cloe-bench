# 5_density-magnification-rsd_x_shear-ia

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
