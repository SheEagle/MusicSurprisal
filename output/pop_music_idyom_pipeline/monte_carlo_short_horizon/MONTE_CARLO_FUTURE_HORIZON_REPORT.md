# Cpitch Monte Carlo Future-Horizon Prediction

This analysis samples intervening cpitch paths up to the true C2 horizon, then scores the actual C2 cpitch incipit after each sampled path.

- Eligible songs: 226
- Folds: 5
- Max order: 8
- Incipit length: 4 cpitch events
- Rollouts: 100
- Timepoints: fixed horizons 1, 2, 4, 8 notes before C2

## Raw Future IC Slope

| Source | N songs | Mean slope per note before C2 [95% CI] | p |
|---|---:|---:|---:|
| ALL | 222 | -0.018 [-0.027, -0.010] | <.001 |
| cocopops_billboard | 104 | -0.024 [-0.039, -0.009] | 0.002 |
| cocopops_rollingstone | 118 | -0.013 [-0.023, -0.004] | 0.006 |

## Raw Future IC Onset

| Source | Horizon | Notes before C2 | Baseline - current future IC [95% CI] | p | Onset |
|---|---:|---:|---:|---:|---:|
| ALL | 2.0 | 2.000 | -0.047 [-0.087, -0.008] | 0.019 | 0 |
| ALL | 1.0 | 1.000 | -0.154 [-0.213, -0.094] | <.001 | 0 |
| cocopops_billboard | 2.0 | 2.000 | -0.051 [-0.112, 0.009] | 0.095 | 0 |
| cocopops_billboard | 1.0 | 1.000 | -0.164 [-0.264, -0.063] | 0.002 | 0 |
| cocopops_rollingstone | 2.0 | 2.000 | -0.044 [-0.097, 0.009] | 0.104 | 0 |
| cocopops_rollingstone | 1.0 | 1.000 | -0.145 [-0.216, -0.075] | <.001 | 0 |

## Relative Future IC, All Songs

| Baseline | Horizon | N | Actual C2 future IC | Baseline future IC | Effect [95% CI] | p |
|---|---:|---:|---:|---:|---:|---:|
| v2_opening | 1.0 | 226 | 3.983 | 4.011 | 0.028 [-0.121, 0.178] | 0.708 |
| v2_opening | 2.0 | 224 | 3.868 | 3.918 | 0.050 [-0.100, 0.200] | 0.512 |
| v2_opening | 4.0 | 222 | 3.809 | 3.827 | 0.018 [-0.142, 0.178] | 0.825 |
| v2_opening | 8.0 | 215 | 3.841 | 3.811 | -0.030 [-0.188, 0.128] | 0.709 |
| other_song_c2 | 1.0 | 226 | 3.983 | 3.728 | -0.255 [-0.395, -0.114] | <.001 |
| other_song_c2 | 2.0 | 224 | 3.868 | 3.553 | -0.315 [-0.455, -0.174] | <.001 |
| other_song_c2 | 4.0 | 222 | 3.809 | 3.484 | -0.325 [-0.470, -0.181] | <.001 |
| other_song_c2 | 8.0 | 215 | 3.841 | 3.497 | -0.344 [-0.495, -0.194] | <.001 |
| shuffled_c2 | 1.0 | 226 | 3.983 | 4.195 | 0.212 [0.103, 0.322] | <.001 |
| shuffled_c2 | 2.0 | 224 | 3.868 | 4.061 | 0.193 [0.098, 0.289] | <.001 |
| shuffled_c2 | 4.0 | 222 | 3.809 | 4.019 | 0.210 [0.120, 0.300] | <.001 |
| shuffled_c2 | 8.0 | 215 | 3.841 | 4.026 | 0.185 [0.099, 0.271] | <.001 |

## Headline

Raw future IC does not get lower closer to C2: slope -0.018 per note before C2, p = <.001. No sustained raw future-IC onset under the 8/4-note horizon baseline. `other_song_c2`: no sustained actual C2 advantage. `shuffled_c2`: actual C2 advantage from horizon 8. `v2_opening`: no sustained actual C2 advantage.