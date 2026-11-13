# 1_density_x_shear

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
