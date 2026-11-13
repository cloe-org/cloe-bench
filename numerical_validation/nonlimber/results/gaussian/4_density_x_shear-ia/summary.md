# 4_density_x_shear-ia

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
