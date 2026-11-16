# 2_density-magnification_x_shear

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
