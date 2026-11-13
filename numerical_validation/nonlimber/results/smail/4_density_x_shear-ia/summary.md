# 4_density_x_shear-ia

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
