# Cpitch Monte Carlo Future-Horizon Prediction

This analysis samples intervening cpitch paths up to the true C2 horizon, then scores the actual C2 cpitch incipit after each sampled path.

- Eligible songs: 226
- Folds: 5
- Max order: 8
- Incipit length: 4 cpitch events
- Rollouts: 1000
- Timepoints: fixed horizons 1, 2, 4, 8 notes before C2
- Raw only: True

## Raw Future IC Slope

| Source | N songs | Mean slope per note before C2 [95% CI] | p |
|---|---:|---:|---:|
| ALL | 222 | -0.024 [-0.032, -0.017] | <.001 |
| cocopops_billboard | 104 | -0.029 [-0.041, -0.016] | <.001 |
| cocopops_rollingstone | 118 | -0.020 [-0.029, -0.012] | <.001 |

## Raw Future IC Onset

| Source | Horizon | Notes before C2 | Baseline - current future IC [95% CI] | p | Onset |
|---|---:|---:|---:|---:|---:|
| ALL | 2.0 | 2.000 | -0.071 [-0.107, -0.034] | <.001 | 0 |
| ALL | 1.0 | 1.000 | -0.193 [-0.249, -0.136] | <.001 | 0 |
| cocopops_billboard | 2.0 | 2.000 | -0.084 [-0.139, -0.030] | 0.003 | 0 |
| cocopops_billboard | 1.0 | 1.000 | -0.216 [-0.311, -0.120] | <.001 | 0 |
| cocopops_rollingstone | 2.0 | 2.000 | -0.059 [-0.108, -0.010] | 0.020 | 0 |
| cocopops_rollingstone | 1.0 | 1.000 | -0.173 [-0.238, -0.107] | <.001 | 0 |

## Headline

Raw future IC does not get lower closer to C2: slope -0.024 per note before C2, p = <.001. No sustained raw future-IC onset under the 8/4-note horizon baseline.