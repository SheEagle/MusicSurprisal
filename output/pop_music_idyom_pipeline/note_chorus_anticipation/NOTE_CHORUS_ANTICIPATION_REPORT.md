# Note-Level Chorus Incipit Anticipation

This analysis asks whether the upcoming C2 opening notes become a more plausible immediate continuation as the preceding section approaches the chorus boundary.

- Eligible songs: 226
- Folds: 5
- Max order: 8
- Incipit length: 4 notes

## Raw C2 IC Slope

| Source | Model | N songs | Mean slope [95% CI] | p |
|---|---|---:|---:|---:|
| ALL | LTM | 226 | -0.083 [-0.218, 0.051] | 0.224 |
| ALL | STM | 226 | -0.266 [-0.355, -0.177] | <.001 |
| ALL | BOTH | 226 | -0.169 [-0.257, -0.082] | <.001 |
| cocopops_billboard | LTM | 108 | -0.128 [-0.338, 0.083] | 0.232 |
| cocopops_billboard | STM | 108 | -0.236 [-0.367, -0.105] | <.001 |
| cocopops_billboard | BOTH | 108 | -0.183 [-0.318, -0.047] | 0.009 |
| cocopops_rollingstone | LTM | 118 | -0.043 [-0.218, 0.132] | 0.627 |
| cocopops_rollingstone | STM | 118 | -0.294 [-0.418, -0.170] | <.001 |
| cocopops_rollingstone | BOTH | 118 | -0.157 [-0.271, -0.044] | 0.007 |

Negative slope means the actual C2 opening becomes less surprising as the preceding section approaches C2.

## Raw C2 IC Onset

Early baseline is the mean of the 10% and 20% bins. Positive values mean the current bin has lower IC than the early-section baseline.

| Source | Model | Bin | Notes before C2 | Baseline - current IC [95% CI] | p | Onset |
|---|---|---:|---:|---:|---:|---:|
| ALL | LTM | 0.3 | 34.487 | -0.002 [-0.121, 0.117] | 0.969 | 0 |
| ALL | LTM | 0.4 | 29.673 | 0.024 [-0.117, 0.166] | 0.735 | 0 |
| ALL | LTM | 0.5 | 24.973 | 0.002 [-0.123, 0.128] | 0.970 | 0 |
| ALL | LTM | 0.6 | 19.978 | -0.029 [-0.153, 0.096] | 0.651 | 0 |
| ALL | LTM | 0.7 | 15.053 | -0.021 [-0.146, 0.104] | 0.738 | 0 |
| ALL | LTM | 0.8 | 10.296 | 0.010 [-0.129, 0.149] | 0.886 | 0 |
| ALL | LTM | 0.9 | 5.385 | 0.070 [-0.070, 0.210] | 0.323 | 0 |
| ALL | LTM | 1.0 | 1.000 | 0.113 [-0.033, 0.259] | 0.129 | 0 |
| ALL | STM | 0.3 | 34.487 | -0.035 [-0.111, 0.042] | 0.371 | 0 |
| ALL | STM | 0.4 | 29.673 | -0.013 [-0.097, 0.072] | 0.770 | 0 |
| ALL | STM | 0.5 | 24.973 | 0.037 [-0.055, 0.129] | 0.432 | 0 |
| ALL | STM | 0.6 | 19.978 | -0.016 [-0.102, 0.069] | 0.710 | 0 |
| ALL | STM | 0.7 | 15.053 | -0.041 [-0.131, 0.050] | 0.374 | 0 |
| ALL | STM | 0.8 | 10.296 | -0.028 [-0.105, 0.050] | 0.482 | 0 |
| ALL | STM | 0.9 | 5.385 | 0.032 [-0.066, 0.130] | 0.525 | 0 |
| ALL | STM | 1.0 | 1.000 | 0.475 [0.371, 0.578] | <.001 | 1 |
| ALL | BOTH | 0.3 | 34.487 | -0.024 [-0.102, 0.054] | 0.550 | 0 |
| ALL | BOTH | 0.4 | 29.673 | -0.041 [-0.132, 0.050] | 0.373 | 0 |
| ALL | BOTH | 0.5 | 24.973 | 0.007 [-0.072, 0.086] | 0.866 | 0 |
| ALL | BOTH | 0.6 | 19.978 | -0.045 [-0.128, 0.038] | 0.285 | 0 |
| ALL | BOTH | 0.7 | 15.053 | -0.047 [-0.131, 0.037] | 0.270 | 0 |
| ALL | BOTH | 0.8 | 10.296 | -0.023 [-0.108, 0.061] | 0.591 | 0 |
| ALL | BOTH | 0.9 | 5.385 | 0.020 [-0.070, 0.111] | 0.659 | 0 |
| ALL | BOTH | 1.0 | 1.000 | 0.302 [0.204, 0.401] | <.001 | 1 |
| cocopops_billboard | LTM | 0.3 | 32.426 | 0.048 [-0.127, 0.222] | 0.588 | 0 |
| cocopops_billboard | LTM | 0.4 | 27.926 | 0.241 [0.030, 0.452] | 0.026 | 0 |
| cocopops_billboard | LTM | 0.5 | 23.509 | 0.018 [-0.172, 0.207] | 0.853 | 0 |
| cocopops_billboard | LTM | 0.6 | 18.796 | 0.020 [-0.171, 0.210] | 0.839 | 0 |
| cocopops_billboard | LTM | 0.7 | 14.148 | 0.070 [-0.118, 0.258] | 0.462 | 0 |
| cocopops_billboard | LTM | 0.8 | 9.722 | 0.049 [-0.154, 0.251] | 0.635 | 0 |
| cocopops_billboard | LTM | 0.9 | 5.065 | 0.198 [-0.010, 0.406] | 0.062 | 0 |
| cocopops_billboard | LTM | 1.0 | 1.000 | 0.141 [-0.075, 0.357] | 0.198 | 0 |
| cocopops_billboard | STM | 0.3 | 32.426 | 0.021 [-0.105, 0.147] | 0.740 | 0 |
| cocopops_billboard | STM | 0.4 | 27.926 | -0.026 [-0.148, 0.096] | 0.673 | 0 |
| cocopops_billboard | STM | 0.5 | 23.509 | 0.051 [-0.107, 0.209] | 0.525 | 0 |
| cocopops_billboard | STM | 0.6 | 18.796 | 0.024 [-0.115, 0.162] | 0.734 | 0 |
| cocopops_billboard | STM | 0.7 | 14.148 | -0.005 [-0.126, 0.115] | 0.930 | 0 |
| cocopops_billboard | STM | 0.8 | 9.722 | -0.031 [-0.148, 0.087] | 0.605 | 0 |
| cocopops_billboard | STM | 0.9 | 5.065 | 0.013 [-0.134, 0.160] | 0.860 | 0 |
| cocopops_billboard | STM | 1.0 | 1.000 | 0.447 [0.287, 0.607] | <.001 | 1 |
| cocopops_billboard | BOTH | 0.3 | 32.426 | 0.020 [-0.095, 0.135] | 0.732 | 0 |
| cocopops_billboard | BOTH | 0.4 | 27.926 | 0.062 [-0.075, 0.199] | 0.370 | 0 |
| cocopops_billboard | BOTH | 0.5 | 23.509 | 0.031 [-0.092, 0.154] | 0.619 | 0 |
| cocopops_billboard | BOTH | 0.6 | 18.796 | -0.041 [-0.165, 0.083] | 0.518 | 0 |
| cocopops_billboard | BOTH | 0.7 | 14.148 | 0.003 [-0.113, 0.119] | 0.958 | 0 |
| cocopops_billboard | BOTH | 0.8 | 9.722 | 0.001 [-0.126, 0.127] | 0.992 | 0 |
| cocopops_billboard | BOTH | 0.9 | 5.065 | 0.086 [-0.058, 0.230] | 0.240 | 0 |
| cocopops_billboard | BOTH | 1.0 | 1.000 | 0.310 [0.160, 0.459] | <.001 | 1 |
| cocopops_rollingstone | LTM | 0.3 | 36.373 | -0.048 [-0.213, 0.116] | 0.563 | 0 |
| cocopops_rollingstone | LTM | 0.4 | 31.271 | -0.174 [-0.360, 0.013] | 0.067 | 0 |
| cocopops_rollingstone | LTM | 0.5 | 26.314 | -0.012 [-0.180, 0.157] | 0.892 | 0 |
| cocopops_rollingstone | LTM | 0.6 | 21.059 | -0.073 [-0.238, 0.093] | 0.386 | 0 |
| cocopops_rollingstone | LTM | 0.7 | 15.881 | -0.105 [-0.272, 0.062] | 0.217 | 0 |
| cocopops_rollingstone | LTM | 0.8 | 10.822 | -0.025 [-0.218, 0.168] | 0.796 | 0 |
| cocopops_rollingstone | LTM | 0.9 | 5.678 | -0.047 [-0.236, 0.142] | 0.626 | 0 |
| cocopops_rollingstone | LTM | 1.0 | 1.000 | 0.087 [-0.114, 0.289] | 0.392 | 0 |
| cocopops_rollingstone | STM | 0.3 | 36.373 | -0.086 [-0.176, 0.004] | 0.062 | 0 |
| cocopops_rollingstone | STM | 0.4 | 31.271 | -0.000 [-0.120, 0.119] | 0.995 | 0 |
| cocopops_rollingstone | STM | 0.5 | 26.314 | 0.024 [-0.079, 0.127] | 0.648 | 0 |
| cocopops_rollingstone | STM | 0.6 | 21.059 | -0.053 [-0.159, 0.053] | 0.325 | 0 |
| cocopops_rollingstone | STM | 0.7 | 15.881 | -0.073 [-0.209, 0.062] | 0.285 | 0 |
| cocopops_rollingstone | STM | 0.8 | 10.822 | -0.025 [-0.129, 0.079] | 0.636 | 0 |
| cocopops_rollingstone | STM | 0.9 | 5.678 | 0.049 [-0.084, 0.181] | 0.470 | 0 |
| cocopops_rollingstone | STM | 1.0 | 1.000 | 0.500 [0.364, 0.636] | <.001 | 1 |
| cocopops_rollingstone | BOTH | 0.3 | 36.373 | -0.064 [-0.171, 0.044] | 0.244 | 0 |
| cocopops_rollingstone | BOTH | 0.4 | 31.271 | -0.135 [-0.255, -0.016] | 0.027 | 0 |
| cocopops_rollingstone | BOTH | 0.5 | 26.314 | -0.015 [-0.118, 0.087] | 0.768 | 0 |
| cocopops_rollingstone | BOTH | 0.6 | 21.059 | -0.049 [-0.163, 0.064] | 0.390 | 0 |
| cocopops_rollingstone | BOTH | 0.7 | 15.881 | -0.093 [-0.214, 0.028] | 0.132 | 0 |
| cocopops_rollingstone | BOTH | 0.8 | 10.822 | -0.045 [-0.159, 0.070] | 0.441 | 0 |
| cocopops_rollingstone | BOTH | 0.9 | 5.678 | -0.040 [-0.154, 0.075] | 0.494 | 0 |
| cocopops_rollingstone | BOTH | 1.0 | 1.000 | 0.296 [0.165, 0.427] | <.001 | 1 |

The effect is `baseline IC - actual C2 opening IC`; positive values mean the actual C2 opening is more probable than the matched baseline.

## BOTH Model, All Songs

| Baseline | Bin | N | Actual C2 IC | Baseline IC | Effect [95% CI] | p |
|---|---:|---:|---:|---:|---:|---:|
| v2_opening | 0.1 | 226 | 3.585 | 3.322 | -0.263 [-0.411, -0.116] | <.001 |
| v2_opening | 0.2 | 226 | 3.587 | 3.233 | -0.354 [-0.494, -0.214] | <.001 |
| v2_opening | 0.3 | 226 | 3.610 | 3.249 | -0.361 [-0.503, -0.219] | <.001 |
| v2_opening | 0.4 | 226 | 3.627 | 3.286 | -0.341 [-0.480, -0.203] | <.001 |
| v2_opening | 0.5 | 226 | 3.579 | 3.287 | -0.293 [-0.439, -0.147] | <.001 |
| v2_opening | 0.6 | 226 | 3.631 | 3.262 | -0.369 [-0.516, -0.222] | <.001 |
| v2_opening | 0.7 | 226 | 3.633 | 3.274 | -0.359 [-0.502, -0.217] | <.001 |
| v2_opening | 0.8 | 226 | 3.609 | 3.321 | -0.288 [-0.428, -0.148] | <.001 |
| v2_opening | 0.9 | 226 | 3.566 | 3.314 | -0.252 [-0.391, -0.112] | <.001 |
| v2_opening | 1.0 | 226 | 3.284 | 3.185 | -0.099 [-0.243, 0.046] | 0.179 |
| other_song_c2 | 0.1 | 226 | 3.585 | 4.610 | 1.025 [0.851, 1.200] | <.001 |
| other_song_c2 | 0.2 | 226 | 3.587 | 4.546 | 0.959 [0.796, 1.121] | <.001 |
| other_song_c2 | 0.3 | 226 | 3.610 | 4.579 | 0.969 [0.806, 1.133] | <.001 |
| other_song_c2 | 0.4 | 226 | 3.627 | 4.575 | 0.948 [0.787, 1.108] | <.001 |
| other_song_c2 | 0.5 | 226 | 3.579 | 4.582 | 1.002 [0.839, 1.166] | <.001 |
| other_song_c2 | 0.6 | 226 | 3.631 | 4.521 | 0.890 [0.717, 1.062] | <.001 |
| other_song_c2 | 0.7 | 226 | 3.633 | 4.618 | 0.985 [0.816, 1.154] | <.001 |
| other_song_c2 | 0.8 | 226 | 3.609 | 4.653 | 1.044 [0.889, 1.199] | <.001 |
| other_song_c2 | 0.9 | 226 | 3.566 | 4.569 | 1.003 [0.832, 1.175] | <.001 |
| other_song_c2 | 1.0 | 226 | 3.284 | 4.515 | 1.231 [1.068, 1.394] | <.001 |
| shuffled_c2 | 0.1 | 226 | 3.585 | 4.049 | 0.464 [0.360, 0.567] | <.001 |
| shuffled_c2 | 0.2 | 226 | 3.587 | 4.054 | 0.467 [0.359, 0.575] | <.001 |
| shuffled_c2 | 0.3 | 226 | 3.610 | 4.097 | 0.487 [0.369, 0.605] | <.001 |
| shuffled_c2 | 0.4 | 226 | 3.627 | 4.022 | 0.395 [0.287, 0.503] | <.001 |
| shuffled_c2 | 0.5 | 226 | 3.579 | 4.014 | 0.434 [0.322, 0.547] | <.001 |
| shuffled_c2 | 0.6 | 226 | 3.631 | 4.065 | 0.433 [0.320, 0.547] | <.001 |
| shuffled_c2 | 0.7 | 226 | 3.633 | 4.007 | 0.374 [0.261, 0.486] | <.001 |
| shuffled_c2 | 0.8 | 226 | 3.609 | 4.032 | 0.423 [0.321, 0.525] | <.001 |
| shuffled_c2 | 0.9 | 226 | 3.566 | 4.066 | 0.500 [0.386, 0.614] | <.001 |
| shuffled_c2 | 1.0 | 226 | 3.284 | 3.920 | 0.637 [0.511, 0.763] | <.001 |

## Headline

Raw BOTH C2 IC decreases: slope -0.169, p = <.001. Sustained raw-IC reduction onset: bin 1.0, about 1.000 notes before C2.

`other_song_c2`: positive from bin 0.1. `shuffled_c2`: positive from bin 0.1. `v2_opening`: no sustained positive advantage.

Interpretation: this is an immediate-start likelihood analysis, not a true future-horizon rollout. It estimates when the C2 incipit becomes compatible with the note-level context before the section begins.