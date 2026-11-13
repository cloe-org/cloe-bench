# 5_density-magnification-rsd_x_shear-ia

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
