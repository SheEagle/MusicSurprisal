# Cpitch Monte Carlo Future-Horizon Prediction

This analysis samples intervening cpitch paths up to the true C2 horizon, then scores the actual C2 cpitch incipit after each sampled path.

- Eligible songs: 226
- Folds: 5
- Max order: 8
- Incipit length: 4 cpitch events
- Rollouts: 100

## Raw Future IC Slope

| Source | N songs | Mean slope [95% CI] | p |
|---|---:|---:|---:|
| ALL | 226 | 0.335 [0.255, 0.414] | <.001 |
| cocopops_billboard | 108 | 0.338 [0.216, 0.460] | <.001 |
| cocopops_rollingstone | 118 | 0.331 [0.225, 0.437] | <.001 |

## Raw Future IC Onset

| Source | Bin | Notes before C2 | Baseline - current future IC [95% CI] | p | Onset |
|---|---:|---:|---:|---:|---:|
| ALL | 0.3 | 33.487 | 0.004 [-0.024, 0.032] | 0.785 | 0 |
| ALL | 0.4 | 28.673 | 0.014 [-0.018, 0.046] | 0.393 | 0 |
| ALL | 0.5 | 23.973 | 0.033 [0.004, 0.062] | 0.027 | 0 |
| ALL | 0.6 | 18.978 | 0.012 [-0.022, 0.046] | 0.492 | 0 |
| ALL | 0.7 | 14.053 | 0.011 [-0.026, 0.049] | 0.552 | 0 |
| ALL | 0.8 | 9.296 | 0.019 [-0.019, 0.058] | 0.320 | 0 |
| ALL | 0.9 | 4.385 | -0.024 [-0.076, 0.028] | 0.361 | 0 |
| ALL | 1.0 | 0.000 | -0.601 [-0.725, -0.477] | <.001 | 0 |
| cocopops_billboard | 0.3 | 31.426 | 0.000 [-0.041, 0.041] | 0.995 | 0 |
| cocopops_billboard | 0.4 | 26.926 | -0.004 [-0.050, 0.042] | 0.864 | 0 |
| cocopops_billboard | 0.5 | 22.509 | 0.051 [0.007, 0.095] | 0.024 | 0 |
| cocopops_billboard | 0.6 | 17.796 | -0.007 [-0.065, 0.052] | 0.826 | 0 |
| cocopops_billboard | 0.7 | 13.148 | 0.005 [-0.060, 0.071] | 0.871 | 0 |
| cocopops_billboard | 0.8 | 8.722 | 0.013 [-0.049, 0.076] | 0.671 | 0 |
| cocopops_billboard | 0.9 | 4.065 | -0.016 [-0.101, 0.069] | 0.711 | 0 |
| cocopops_billboard | 1.0 | 0.000 | -0.614 [-0.794, -0.435] | <.001 | 0 |
| cocopops_rollingstone | 0.3 | 35.373 | 0.007 [-0.031, 0.046] | 0.709 | 0 |
| cocopops_rollingstone | 0.4 | 30.271 | 0.030 [-0.016, 0.077] | 0.193 | 0 |
| cocopops_rollingstone | 0.5 | 25.314 | 0.017 [-0.022, 0.056] | 0.399 | 0 |
| cocopops_rollingstone | 0.6 | 20.059 | 0.029 [-0.009, 0.067] | 0.137 | 0 |
| cocopops_rollingstone | 0.7 | 14.881 | 0.017 [-0.024, 0.057] | 0.414 | 0 |
| cocopops_rollingstone | 0.8 | 9.822 | 0.025 [-0.022, 0.071] | 0.296 | 0 |
| cocopops_rollingstone | 0.9 | 4.678 | -0.031 [-0.094, 0.031] | 0.319 | 0 |
| cocopops_rollingstone | 1.0 | 0.000 | -0.589 [-0.764, -0.414] | <.001 | 0 |

## Relative Future IC, All Songs

| Baseline | Bin | N | Actual C2 future IC | Baseline future IC | Effect [95% CI] | p |
|---|---:|---:|---:|---:|---:|---:|
| v2_opening | 0.1 | 226 | 3.865 | 3.832 | -0.033 [-0.188, 0.122] | 0.676 |
| v2_opening | 0.2 | 226 | 3.854 | 3.829 | -0.026 [-0.180, 0.128] | 0.743 |
| v2_opening | 0.3 | 226 | 3.856 | 3.834 | -0.022 [-0.178, 0.135] | 0.784 |
| v2_opening | 0.4 | 226 | 3.845 | 3.840 | -0.006 [-0.160, 0.148] | 0.942 |
| v2_opening | 0.5 | 226 | 3.826 | 3.836 | 0.010 [-0.140, 0.160] | 0.896 |
| v2_opening | 0.6 | 226 | 3.847 | 3.863 | 0.016 [-0.143, 0.174] | 0.847 |
| v2_opening | 0.7 | 226 | 3.848 | 3.870 | 0.021 [-0.133, 0.176] | 0.784 |
| v2_opening | 0.8 | 226 | 3.840 | 3.851 | 0.011 [-0.143, 0.165] | 0.889 |
| v2_opening | 0.9 | 226 | 3.883 | 3.910 | 0.026 [-0.126, 0.179] | 0.734 |
| v2_opening | 1.0 | 226 | 4.461 | 4.533 | 0.072 [-0.116, 0.260] | 0.451 |
| other_song_c2 | 0.1 | 226 | 3.865 | 3.486 | -0.378 [-0.523, -0.233] | <.001 |
| other_song_c2 | 0.2 | 226 | 3.854 | 3.523 | -0.332 [-0.472, -0.192] | <.001 |
| other_song_c2 | 0.3 | 226 | 3.856 | 3.506 | -0.350 [-0.492, -0.207] | <.001 |
| other_song_c2 | 0.4 | 226 | 3.845 | 3.518 | -0.328 [-0.468, -0.188] | <.001 |
| other_song_c2 | 0.5 | 226 | 3.826 | 3.504 | -0.322 [-0.459, -0.186] | <.001 |
| other_song_c2 | 0.6 | 226 | 3.847 | 3.530 | -0.317 [-0.460, -0.175] | <.001 |
| other_song_c2 | 0.7 | 226 | 3.848 | 3.545 | -0.303 [-0.445, -0.161] | <.001 |
| other_song_c2 | 0.8 | 226 | 3.840 | 3.547 | -0.294 [-0.434, -0.153] | <.001 |
| other_song_c2 | 0.9 | 226 | 3.883 | 3.583 | -0.300 [-0.440, -0.160] | <.001 |
| other_song_c2 | 1.0 | 226 | 4.461 | 4.269 | -0.192 [-0.369, -0.015] | 0.034 |
| shuffled_c2 | 0.1 | 226 | 3.865 | 4.028 | 0.163 [0.073, 0.253] | <.001 |
| shuffled_c2 | 0.2 | 226 | 3.854 | 4.032 | 0.178 [0.090, 0.266] | <.001 |
| shuffled_c2 | 0.3 | 226 | 3.856 | 4.037 | 0.181 [0.090, 0.273] | <.001 |
| shuffled_c2 | 0.4 | 226 | 3.845 | 4.038 | 0.193 [0.105, 0.280] | <.001 |
| shuffled_c2 | 0.5 | 226 | 3.826 | 4.008 | 0.182 [0.094, 0.269] | <.001 |
| shuffled_c2 | 0.6 | 226 | 3.847 | 4.042 | 0.195 [0.101, 0.289] | <.001 |
| shuffled_c2 | 0.7 | 226 | 3.848 | 4.045 | 0.197 [0.109, 0.286] | <.001 |
| shuffled_c2 | 0.8 | 226 | 3.840 | 4.041 | 0.201 [0.116, 0.285] | <.001 |
| shuffled_c2 | 0.9 | 226 | 3.883 | 4.091 | 0.207 [0.107, 0.307] | <.001 |
| shuffled_c2 | 1.0 | 226 | 4.461 | 4.645 | 0.184 [0.023, 0.346] | 0.026 |

## Headline

Raw future IC does not decrease: slope 0.335, p = <.001. No sustained raw future-IC onset under the 10/20% baseline criterion. `other_song_c2`: no sustained actual C2 advantage. `shuffled_c2`: actual C2 advantage from bin 0.1. `v2_opening`: no sustained actual C2 advantage.