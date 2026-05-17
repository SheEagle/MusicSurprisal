# experiment2_chorus_onset_vs_body_cluster_robust

Formula:

```text
IC2_ij = b0 + b1*IC1_c_ij + b2*Condition_ij
       + b3*(IC1_c_ij * Condition_ij)
       + b4*within_position_c_ij
       + b5*(IC1_c_ij * within_position_c_ij)
       + b6*pitch_similarity_c_ij
       + b7*mean_onset_position_c_ij + error_ij
```

Standard errors are clustered by song (`piece_id`).

| Experiment | Corpus | Model | Term | N notes | Song clusters | Estimate [95% CI] | SE | p |
|---|---|---|---|---:|---:|---:|---:|---:|
| experiment2_chorus_onset_vs_body | Billboard | LTM | b0 | 1399 | 156 | 3.363 [3.216, 3.509] | 0.074 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | LTM | b1 | 1399 | 156 | 0.755 [0.645, 0.866] | 0.056 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | LTM | b2 | 1399 | 156 | -0.010 [-0.346, 0.327] | 0.170 | 0.955 |
| experiment2_chorus_onset_vs_body | Billboard | LTM | b3 | 1399 | 156 | -0.078 [-0.264, 0.107] | 0.094 | 0.405 |
| experiment2_chorus_onset_vs_body | Billboard | LTM | b4 | 1399 | 156 | -0.027 [-0.088, 0.035] | 0.031 | 0.394 |
| experiment2_chorus_onset_vs_body | Billboard | LTM | b5 | 1399 | 156 | -0.013 [-0.048, 0.022] | 0.018 | 0.480 |
| experiment2_chorus_onset_vs_body | Billboard | LTM | b6 | 1399 | 156 | -0.043 [-0.515, 0.429] | 0.239 | 0.857 |
| experiment2_chorus_onset_vs_body | Billboard | LTM | b7 | 1399 | 156 | -0.049 [-0.642, 0.545] | 0.301 | 0.872 |
| experiment2_chorus_onset_vs_body | Billboard | LTM+ | b0 | 1399 | 156 | 2.123 [1.932, 2.313] | 0.097 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | LTM+ | b1 | 1399 | 156 | 0.236 [0.130, 0.343] | 0.054 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | LTM+ | b2 | 1399 | 156 | -0.074 [-0.424, 0.277] | 0.177 | 0.678 |
| experiment2_chorus_onset_vs_body | Billboard | LTM+ | b3 | 1399 | 156 | -0.069 [-0.285, 0.147] | 0.109 | 0.529 |
| experiment2_chorus_onset_vs_body | Billboard | LTM+ | b4 | 1399 | 156 | -0.157 [-0.215, -0.100] | 0.029 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | LTM+ | b5 | 1399 | 156 | -0.032 [-0.063, -0.001] | 0.016 | 0.042 |
| experiment2_chorus_onset_vs_body | Billboard | LTM+ | b6 | 1399 | 156 | -1.744 [-2.301, -1.188] | 0.282 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | LTM+ | b7 | 1399 | 156 | -0.621 [-1.510, 0.268] | 0.450 | 0.170 |
| experiment2_chorus_onset_vs_body | Billboard | BOTH+ | b0 | 1399 | 156 | 1.572 [1.390, 1.754] | 0.092 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | BOTH+ | b1 | 1399 | 156 | 0.147 [0.066, 0.229] | 0.041 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | BOTH+ | b2 | 1399 | 156 | -0.064 [-0.389, 0.261] | 0.165 | 0.698 |
| experiment2_chorus_onset_vs_body | Billboard | BOTH+ | b3 | 1399 | 156 | -0.044 [-0.206, 0.117] | 0.082 | 0.589 |
| experiment2_chorus_onset_vs_body | Billboard | BOTH+ | b4 | 1399 | 156 | -0.127 [-0.178, -0.077] | 0.026 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | BOTH+ | b5 | 1399 | 156 | -0.031 [-0.055, -0.007] | 0.012 | 0.013 |
| experiment2_chorus_onset_vs_body | Billboard | BOTH+ | b6 | 1399 | 156 | -2.349 [-2.896, -1.803] | 0.277 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | BOTH+ | b7 | 1399 | 156 | -0.154 [-0.983, 0.676] | 0.420 | 0.715 |
| experiment2_chorus_onset_vs_body | Billboard | STM | b0 | 1399 | 156 | 1.549 [1.410, 1.688] | 0.070 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | STM | b1 | 1399 | 156 | 0.072 [0.014, 0.131] | 0.030 | 0.016 |
| experiment2_chorus_onset_vs_body | Billboard | STM | b2 | 1399 | 156 | 0.037 [-0.213, 0.288] | 0.127 | 0.768 |
| experiment2_chorus_onset_vs_body | Billboard | STM | b3 | 1399 | 156 | -0.027 [-0.142, 0.089] | 0.059 | 0.648 |
| experiment2_chorus_onset_vs_body | Billboard | STM | b4 | 1399 | 156 | -0.083 [-0.128, -0.039] | 0.022 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | STM | b5 | 1399 | 156 | -0.029 [-0.050, -0.008] | 0.010 | 0.006 |
| experiment2_chorus_onset_vs_body | Billboard | STM | b6 | 1399 | 156 | -2.968 [-3.569, -2.367] | 0.304 | < .001 |
| experiment2_chorus_onset_vs_body | Billboard | STM | b7 | 1399 | 156 | 0.189 [-0.502, 0.880] | 0.350 | 0.589 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM | b0 | 1116 | 124 | 3.084 [2.903, 3.264] | 0.091 | < .001 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM | b1 | 1116 | 124 | 0.645 [0.459, 0.831] | 0.094 | < .001 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM | b2 | 1116 | 124 | 0.275 [-0.100, 0.650] | 0.189 | 0.150 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM | b3 | 1116 | 124 | -0.090 [-0.421, 0.240] | 0.167 | 0.589 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM | b4 | 1116 | 124 | 0.038 [-0.037, 0.112] | 0.038 | 0.320 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM | b5 | 1116 | 124 | -0.022 [-0.074, 0.031] | 0.027 | 0.416 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM | b6 | 1116 | 124 | -0.516 [-1.025, -0.006] | 0.257 | 0.047 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM | b7 | 1116 | 124 | 0.246 [-0.930, 1.421] | 0.594 | 0.680 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM+ | b0 | 1116 | 124 | 2.125 [1.969, 2.282] | 0.079 | < .001 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM+ | b1 | 1116 | 124 | 0.154 [0.063, 0.245] | 0.046 | 0.001 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM+ | b2 | 1116 | 124 | 0.362 [0.068, 0.656] | 0.148 | 0.016 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM+ | b3 | 1116 | 124 | 0.032 [-0.122, 0.186] | 0.078 | 0.683 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM+ | b4 | 1116 | 124 | -0.030 [-0.093, 0.032] | 0.032 | 0.337 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM+ | b5 | 1116 | 124 | -0.037 [-0.071, -0.003] | 0.017 | 0.034 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM+ | b6 | 1116 | 124 | -1.911 [-2.377, -1.445] | 0.235 | < .001 |
| experiment2_chorus_onset_vs_body | RollingStone | LTM+ | b7 | 1116 | 124 | 0.170 [-1.131, 1.470] | 0.657 | 0.796 |
| experiment2_chorus_onset_vs_body | RollingStone | BOTH+ | b0 | 1116 | 124 | 1.577 [1.427, 1.727] | 0.076 | < .001 |
| experiment2_chorus_onset_vs_body | RollingStone | BOTH+ | b1 | 1116 | 124 | 0.101 [0.031, 0.171] | 0.036 | 0.005 |
| experiment2_chorus_onset_vs_body | RollingStone | BOTH+ | b2 | 1116 | 124 | 0.530 [0.239, 0.822] | 0.147 | < .001 |
| experiment2_chorus_onset_vs_body | RollingStone | BOTH+ | b3 | 1116 | 124 | 0.033 [-0.114, 0.179] | 0.074 | 0.661 |
| experiment2_chorus_onset_vs_body | RollingStone | BOTH+ | b4 | 1116 | 124 | -0.007 [-0.062, 0.049] | 0.028 | 0.815 |
| experiment2_chorus_onset_vs_body | RollingStone | BOTH+ | b5 | 1116 | 124 | -0.026 [-0.055, 0.002] | 0.014 | 0.071 |
| experiment2_chorus_onset_vs_body | RollingStone | BOTH+ | b6 | 1116 | 124 | -2.339 [-2.828, -1.850] | 0.247 | < .001 |
| experiment2_chorus_onset_vs_body | RollingStone | BOTH+ | b7 | 1116 | 124 | 0.410 [-0.854, 1.675] | 0.639 | 0.522 |
| experiment2_chorus_onset_vs_body | RollingStone | STM | b0 | 1116 | 124 | 1.667 [1.489, 1.845] | 0.090 | < .001 |
| experiment2_chorus_onset_vs_body | RollingStone | STM | b1 | 1116 | 124 | 0.044 [-0.043, 0.132] | 0.044 | 0.317 |
| experiment2_chorus_onset_vs_body | RollingStone | STM | b2 | 1116 | 124 | 0.428 [0.138, 0.718] | 0.146 | 0.004 |
| experiment2_chorus_onset_vs_body | RollingStone | STM | b3 | 1116 | 124 | 0.016 [-0.160, 0.193] | 0.089 | 0.854 |
| experiment2_chorus_onset_vs_body | RollingStone | STM | b4 | 1116 | 124 | -0.018 [-0.073, 0.036] | 0.028 | 0.505 |
| experiment2_chorus_onset_vs_body | RollingStone | STM | b5 | 1116 | 124 | -0.002 [-0.035, 0.031] | 0.017 | 0.898 |
| experiment2_chorus_onset_vs_body | RollingStone | STM | b6 | 1116 | 124 | -2.691 [-3.321, -2.061] | 0.318 | < .001 |
| experiment2_chorus_onset_vs_body | RollingStone | STM | b7 | 1116 | 124 | 0.328 [-0.717, 1.373] | 0.528 | 0.536 |