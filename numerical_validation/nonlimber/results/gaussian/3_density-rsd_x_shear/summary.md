# 3_density-rsd_x_shear

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
