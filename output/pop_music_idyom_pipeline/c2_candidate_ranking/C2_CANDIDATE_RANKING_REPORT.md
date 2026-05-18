# C2 Candidate-Ranking Analysis

At fixed true pre-C2 contexts, this analysis scores candidate 4-cpitch openings as immediate continuations.

- Eligible songs: 222
- Folds: 5
- Max order: 8
- Incipit length: 4 cpitch events
- Horizons: 16, 8, 4, 2, 1 notes before C2
- Candidates: actual_C2, V2_opening, C1_opening, same_song_nonchorus_matched, shuffled_C2

## Actual C2 Rank

| Source | Horizon | N | Mean rank [95% CI] | Top-1 | Top-2 |
|---|---:|---:|---:|---:|---:|
| ALL | 16 | 221 | 2.303 [2.149, 2.457] | 0.321 | 0.579 |
| ALL | 8 | 222 | 2.293 [2.145, 2.441] | 0.306 | 0.577 |
| ALL | 4 | 222 | 2.351 [2.194, 2.509] | 0.297 | 0.599 |
| ALL | 2 | 222 | 2.279 [2.121, 2.437] | 0.338 | 0.613 |
| ALL | 1 | 222 | 2.347 [2.195, 2.499] | 0.302 | 0.554 |
| cocopops_billboard | 16 | 105 | 2.190 [1.977, 2.404] | 0.343 | 0.619 |
| cocopops_billboard | 8 | 105 | 2.086 [1.892, 2.279] | 0.352 | 0.657 |
| cocopops_billboard | 4 | 105 | 2.162 [1.940, 2.383] | 0.371 | 0.657 |
| cocopops_billboard | 2 | 105 | 2.248 [2.011, 2.484] | 0.362 | 0.629 |
| cocopops_billboard | 1 | 105 | 2.200 [2.000, 2.400] | 0.324 | 0.590 |
| cocopops_rollingstone | 16 | 116 | 2.405 [2.183, 2.627] | 0.302 | 0.543 |
| cocopops_rollingstone | 8 | 117 | 2.479 [2.261, 2.696] | 0.265 | 0.504 |
| cocopops_rollingstone | 4 | 117 | 2.521 [2.300, 2.743] | 0.231 | 0.547 |
| cocopops_rollingstone | 2 | 117 | 2.308 [2.093, 2.522] | 0.316 | 0.598 |
| cocopops_rollingstone | 1 | 117 | 2.479 [2.252, 2.705] | 0.282 | 0.521 |

## Margins: Control IC - Actual C2 IC

| Source | Control | Horizon | N | Margin [95% CI] | p |
|---|---|---:|---:|---:|---:|
| ALL | v2_opening | 16 | 221 | -0.097 [-0.298, 0.104] | 0.342 |
| ALL | v2_opening | 8 | 222 | 0.083 [-0.118, 0.284] | 0.417 |
| ALL | v2_opening | 4 | 222 | -0.060 [-0.259, 0.139] | 0.554 |
| ALL | v2_opening | 2 | 222 | 0.061 [-0.119, 0.240] | 0.506 |
| ALL | v2_opening | 1 | 222 | 0.142 [-0.039, 0.322] | 0.124 |
| ALL | c1_opening | 16 | 221 | -0.027 [-0.150, 0.097] | 0.669 |
| ALL | c1_opening | 8 | 222 | 0.019 [-0.087, 0.126] | 0.722 |
| ALL | c1_opening | 4 | 222 | -0.036 [-0.165, 0.094] | 0.588 |
| ALL | c1_opening | 2 | 222 | 0.013 [-0.088, 0.114] | 0.801 |
| ALL | c1_opening | 1 | 222 | -0.060 [-0.167, 0.047] | 0.270 |
| ALL | same_song_nonchorus_matched | 16 | 221 | -0.070 [-0.212, 0.072] | 0.332 |
| ALL | same_song_nonchorus_matched | 8 | 222 | -0.015 [-0.142, 0.112] | 0.815 |
| ALL | same_song_nonchorus_matched | 4 | 222 | -0.092 [-0.239, 0.054] | 0.216 |
| ALL | same_song_nonchorus_matched | 2 | 222 | -0.041 [-0.165, 0.084] | 0.522 |
| ALL | same_song_nonchorus_matched | 1 | 222 | -0.052 [-0.181, 0.078] | 0.432 |
| ALL | shuffled_c2 | 16 | 221 | 0.152 [0.027, 0.277] | 0.018 |
| ALL | shuffled_c2 | 8 | 222 | 0.166 [0.028, 0.303] | 0.019 |
| ALL | shuffled_c2 | 4 | 222 | 0.197 [0.062, 0.332] | 0.004 |
| ALL | shuffled_c2 | 2 | 222 | 0.105 [-0.028, 0.239] | 0.121 |
| ALL | shuffled_c2 | 1 | 222 | 0.215 [0.073, 0.356] | 0.003 |
| cocopops_billboard | v2_opening | 16 | 105 | 0.091 [-0.202, 0.385] | 0.538 |
| cocopops_billboard | v2_opening | 8 | 105 | 0.206 [-0.095, 0.506] | 0.178 |
| cocopops_billboard | v2_opening | 4 | 105 | 0.120 [-0.160, 0.400] | 0.397 |
| cocopops_billboard | v2_opening | 2 | 105 | 0.061 [-0.201, 0.322] | 0.646 |
| cocopops_billboard | v2_opening | 1 | 105 | 0.307 [0.050, 0.564] | 0.020 |
| cocopops_billboard | c1_opening | 16 | 105 | 0.072 [-0.095, 0.238] | 0.394 |
| cocopops_billboard | c1_opening | 8 | 105 | 0.121 [0.004, 0.237] | 0.042 |
| cocopops_billboard | c1_opening | 4 | 105 | -0.000 [-0.138, 0.137] | 0.995 |
| cocopops_billboard | c1_opening | 2 | 105 | 0.082 [-0.066, 0.229] | 0.276 |
| cocopops_billboard | c1_opening | 1 | 105 | 0.025 [-0.104, 0.154] | 0.699 |
| cocopops_billboard | same_song_nonchorus_matched | 16 | 105 | -0.070 [-0.265, 0.124] | 0.475 |
| cocopops_billboard | same_song_nonchorus_matched | 8 | 105 | 0.036 [-0.146, 0.218] | 0.696 |
| cocopops_billboard | same_song_nonchorus_matched | 4 | 105 | -0.165 [-0.374, 0.044] | 0.120 |
| cocopops_billboard | same_song_nonchorus_matched | 2 | 105 | -0.193 [-0.359, -0.027] | 0.023 |
| cocopops_billboard | same_song_nonchorus_matched | 1 | 105 | -0.026 [-0.199, 0.148] | 0.769 |
| cocopops_billboard | shuffled_c2 | 16 | 105 | 0.228 [0.054, 0.402] | 0.011 |
| cocopops_billboard | shuffled_c2 | 8 | 105 | 0.271 [0.073, 0.469] | 0.008 |
| cocopops_billboard | shuffled_c2 | 4 | 105 | 0.321 [0.108, 0.534] | 0.004 |
| cocopops_billboard | shuffled_c2 | 2 | 105 | 0.164 [-0.025, 0.353] | 0.088 |
| cocopops_billboard | shuffled_c2 | 1 | 105 | 0.181 [-0.019, 0.381] | 0.076 |
| cocopops_rollingstone | v2_opening | 16 | 116 | -0.268 [-0.545, 0.009] | 0.058 |
| cocopops_rollingstone | v2_opening | 8 | 117 | -0.027 [-0.300, 0.246] | 0.845 |
| cocopops_rollingstone | v2_opening | 4 | 117 | -0.222 [-0.505, 0.062] | 0.124 |
| cocopops_rollingstone | v2_opening | 2 | 117 | 0.060 [-0.190, 0.311] | 0.633 |
| cocopops_rollingstone | v2_opening | 1 | 117 | -0.007 [-0.261, 0.248] | 0.957 |
| cocopops_rollingstone | c1_opening | 16 | 116 | -0.116 [-0.298, 0.065] | 0.207 |
| cocopops_rollingstone | c1_opening | 8 | 117 | -0.072 [-0.245, 0.101] | 0.412 |
| cocopops_rollingstone | c1_opening | 4 | 117 | -0.067 [-0.282, 0.147] | 0.535 |
| cocopops_rollingstone | c1_opening | 2 | 117 | -0.049 [-0.189, 0.091] | 0.493 |
| cocopops_rollingstone | c1_opening | 1 | 117 | -0.136 [-0.303, 0.030] | 0.108 |
| cocopops_rollingstone | same_song_nonchorus_matched | 16 | 116 | -0.070 [-0.278, 0.139] | 0.508 |
| cocopops_rollingstone | same_song_nonchorus_matched | 8 | 117 | -0.061 [-0.239, 0.118] | 0.502 |
| cocopops_rollingstone | same_song_nonchorus_matched | 4 | 117 | -0.027 [-0.236, 0.181] | 0.795 |
| cocopops_rollingstone | same_song_nonchorus_matched | 2 | 117 | 0.096 [-0.086, 0.279] | 0.298 |
| cocopops_rollingstone | same_song_nonchorus_matched | 1 | 117 | -0.075 [-0.267, 0.117] | 0.442 |
| cocopops_rollingstone | shuffled_c2 | 16 | 116 | 0.083 [-0.097, 0.264] | 0.362 |
| cocopops_rollingstone | shuffled_c2 | 8 | 117 | 0.071 [-0.122, 0.264] | 0.468 |
| cocopops_rollingstone | shuffled_c2 | 4 | 117 | 0.086 [-0.084, 0.256] | 0.319 |
| cocopops_rollingstone | shuffled_c2 | 2 | 117 | 0.053 [-0.138, 0.244] | 0.584 |
| cocopops_rollingstone | shuffled_c2 | 1 | 117 | 0.245 [0.044, 0.447] | 0.018 |

## Headline

At 1 note before C2, actual C2 mean rank is 2.347; top-1 rate is 0.302. It significantly beats 1 of 4 controls at this horizon.