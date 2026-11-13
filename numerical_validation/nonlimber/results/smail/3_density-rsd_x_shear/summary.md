# 3_density-rsd_x_shear

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
