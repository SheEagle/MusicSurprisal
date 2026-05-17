# experiment1_chorus_vs_ordinary_cluster_robust

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
| experiment1_chorus_vs_ordinary | Billboard | LTM | b0 | 2847 | 102 | 3.106 [3.038, 3.174] | 0.034 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | LTM | b1 | 2847 | 102 | 0.848 [0.798, 0.897] | 0.025 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | LTM | b2 | 2847 | 102 | 0.096 [-0.057, 0.248] | 0.077 | 0.217 |
| experiment1_chorus_vs_ordinary | Billboard | LTM | b3 | 2847 | 102 | -0.090 [-0.239, 0.058] | 0.075 | 0.229 |
| experiment1_chorus_vs_ordinary | Billboard | LTM | b4 | 2847 | 102 | -0.042 [-0.100, 0.015] | 0.029 | 0.146 |
| experiment1_chorus_vs_ordinary | Billboard | LTM | b5 | 2847 | 102 | 0.124 [0.073, 0.174] | 0.025 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | LTM | b6 | 2847 | 102 | -0.060 [-1.211, 1.092] | 0.580 | 0.918 |
| experiment1_chorus_vs_ordinary | Billboard | LTM | b7 | 2847 | 102 | 0.042 [-0.273, 0.356] | 0.159 | 0.793 |
| experiment1_chorus_vs_ordinary | Billboard | LTM+ | b0 | 2847 | 102 | 1.934 [1.820, 2.047] | 0.057 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | LTM+ | b1 | 2847 | 102 | 0.331 [0.261, 0.400] | 0.035 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | LTM+ | b2 | 2847 | 102 | 0.132 [-0.078, 0.342] | 0.106 | 0.216 |
| experiment1_chorus_vs_ordinary | Billboard | LTM+ | b3 | 2847 | 102 | -0.062 [-0.190, 0.066] | 0.065 | 0.341 |
| experiment1_chorus_vs_ordinary | Billboard | LTM+ | b4 | 2847 | 102 | -0.159 [-0.205, -0.112] | 0.024 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | LTM+ | b5 | 2847 | 102 | 0.021 [-0.015, 0.057] | 0.018 | 0.248 |
| experiment1_chorus_vs_ordinary | Billboard | LTM+ | b6 | 2847 | 102 | -1.878 [-3.007, -0.749] | 0.569 | 0.001 |
| experiment1_chorus_vs_ordinary | Billboard | LTM+ | b7 | 2847 | 102 | -0.606 [-1.276, 0.064] | 0.338 | 0.076 |
| experiment1_chorus_vs_ordinary | Billboard | BOTH+ | b0 | 2847 | 102 | 1.367 [1.276, 1.457] | 0.046 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | BOTH+ | b1 | 2847 | 102 | 0.206 [0.169, 0.243] | 0.019 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | BOTH+ | b2 | 2847 | 102 | 0.038 [-0.139, 0.216] | 0.090 | 0.670 |
| experiment1_chorus_vs_ordinary | Billboard | BOTH+ | b3 | 2847 | 102 | 0.021 [-0.078, 0.119] | 0.050 | 0.677 |
| experiment1_chorus_vs_ordinary | Billboard | BOTH+ | b4 | 2847 | 102 | -0.162 [-0.208, -0.116] | 0.023 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | BOTH+ | b5 | 2847 | 102 | 0.004 [-0.023, 0.032] | 0.014 | 0.751 |
| experiment1_chorus_vs_ordinary | Billboard | BOTH+ | b6 | 2847 | 102 | -2.670 [-3.837, -1.504] | 0.588 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | BOTH+ | b7 | 2847 | 102 | -0.316 [-0.792, 0.160] | 0.240 | 0.190 |
| experiment1_chorus_vs_ordinary | Billboard | STM | b0 | 2847 | 102 | 1.316 [1.247, 1.385] | 0.035 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | STM | b1 | 2847 | 102 | 0.150 [0.121, 0.180] | 0.015 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | STM | b2 | 2847 | 102 | -0.035 [-0.180, 0.110] | 0.073 | 0.632 |
| experiment1_chorus_vs_ordinary | Billboard | STM | b3 | 2847 | 102 | -0.013 [-0.091, 0.064] | 0.039 | 0.735 |
| experiment1_chorus_vs_ordinary | Billboard | STM | b4 | 2847 | 102 | -0.142 [-0.177, -0.107] | 0.018 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | STM | b5 | 2847 | 102 | -0.017 [-0.034, 0.001] | 0.009 | 0.061 |
| experiment1_chorus_vs_ordinary | Billboard | STM | b6 | 2847 | 102 | -3.667 [-5.189, -2.144] | 0.767 | < .001 |
| experiment1_chorus_vs_ordinary | Billboard | STM | b7 | 2847 | 102 | 0.018 [-0.339, 0.375] | 0.180 | 0.922 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM | b0 | 2883 | 110 | 3.046 [2.981, 3.111] | 0.033 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM | b1 | 2883 | 110 | 0.855 [0.792, 0.918] | 0.032 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM | b2 | 2883 | 110 | 0.117 [-0.075, 0.308] | 0.097 | 0.229 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM | b3 | 2883 | 110 | -0.196 [-0.334, -0.058] | 0.070 | 0.006 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM | b4 | 2883 | 110 | 0.004 [-0.046, 0.054] | 0.025 | 0.871 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM | b5 | 2883 | 110 | 0.117 [0.064, 0.171] | 0.027 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM | b6 | 2883 | 110 | -0.643 [-1.336, 0.050] | 0.350 | 0.068 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM | b7 | 2883 | 110 | 0.132 [-0.156, 0.420] | 0.145 | 0.366 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM+ | b0 | 2883 | 110 | 2.010 [1.899, 2.122] | 0.056 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM+ | b1 | 2883 | 110 | 0.375 [0.297, 0.453] | 0.039 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM+ | b2 | 2883 | 110 | 0.187 [-0.042, 0.415] | 0.115 | 0.108 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM+ | b3 | 2883 | 110 | -0.068 [-0.203, 0.067] | 0.068 | 0.318 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM+ | b4 | 2883 | 110 | -0.166 [-0.206, -0.125] | 0.020 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM+ | b5 | 2883 | 110 | -0.006 [-0.050, 0.038] | 0.022 | 0.798 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM+ | b6 | 2883 | 110 | -1.950 [-2.720, -1.179] | 0.389 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | LTM+ | b7 | 2883 | 110 | 0.417 [-0.119, 0.953] | 0.270 | 0.126 |
| experiment1_chorus_vs_ordinary | RollingStone | BOTH+ | b0 | 2883 | 110 | 1.448 [1.354, 1.542] | 0.047 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | BOTH+ | b1 | 2883 | 110 | 0.265 [0.210, 0.320] | 0.028 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | BOTH+ | b2 | 2883 | 110 | 0.145 [-0.046, 0.335] | 0.096 | 0.135 |
| experiment1_chorus_vs_ordinary | RollingStone | BOTH+ | b3 | 2883 | 110 | -0.057 [-0.165, 0.051] | 0.054 | 0.295 |
| experiment1_chorus_vs_ordinary | RollingStone | BOTH+ | b4 | 2883 | 110 | -0.185 [-0.231, -0.140] | 0.023 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | BOTH+ | b5 | 2883 | 110 | -0.019 [-0.055, 0.017] | 0.018 | 0.297 |
| experiment1_chorus_vs_ordinary | RollingStone | BOTH+ | b6 | 2883 | 110 | -2.724 [-3.519, -1.929] | 0.401 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | BOTH+ | b7 | 2883 | 110 | 0.664 [0.262, 1.067] | 0.203 | 0.001 |
| experiment1_chorus_vs_ordinary | RollingStone | STM | b0 | 2883 | 110 | 1.402 [1.332, 1.473] | 0.036 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | STM | b1 | 2883 | 110 | 0.145 [0.110, 0.181] | 0.018 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | STM | b2 | 2883 | 110 | 0.129 [-0.030, 0.288] | 0.080 | 0.110 |
| experiment1_chorus_vs_ordinary | RollingStone | STM | b3 | 2883 | 110 | -0.067 [-0.141, 0.007] | 0.038 | 0.077 |
| experiment1_chorus_vs_ordinary | RollingStone | STM | b4 | 2883 | 110 | -0.164 [-0.202, -0.126] | 0.019 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | STM | b5 | 2883 | 110 | -0.002 [-0.024, 0.019] | 0.011 | 0.816 |
| experiment1_chorus_vs_ordinary | RollingStone | STM | b6 | 2883 | 110 | -3.155 [-4.132, -2.177] | 0.493 | < .001 |
| experiment1_chorus_vs_ordinary | RollingStone | STM | b7 | 2883 | 110 | 0.538 [0.277, 0.800] | 0.132 | < .001 |