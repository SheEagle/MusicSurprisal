# experiment3_verse_vs_chorus_cluster_robust

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
| experiment3_verse_vs_chorus | Billboard | LTM | b0 | 2119 | 118 | 3.285 [3.174, 3.396] | 0.056 | < .001 |
| experiment3_verse_vs_chorus | Billboard | LTM | b1 | 2119 | 118 | 0.782 [0.694, 0.871] | 0.045 | < .001 |
| experiment3_verse_vs_chorus | Billboard | LTM | b2 | 2119 | 118 | 0.030 [-0.144, 0.204] | 0.088 | 0.736 |
| experiment3_verse_vs_chorus | Billboard | LTM | b3 | 2119 | 118 | -0.315 [-0.457, -0.173] | 0.071 | < .001 |
| experiment3_verse_vs_chorus | Billboard | LTM | b4 | 2119 | 118 | -0.065 [-0.097, -0.033] | 0.016 | < .001 |
| experiment3_verse_vs_chorus | Billboard | LTM | b5 | 2119 | 118 | -0.011 [-0.030, 0.008] | 0.010 | 0.256 |
| experiment3_verse_vs_chorus | Billboard | LTM | b6 | 2119 | 118 | -0.095 [-0.455, 0.264] | 0.182 | 0.601 |
| experiment3_verse_vs_chorus | Billboard | LTM | b7 | 2119 | 118 | 0.200 [-0.374, 0.773] | 0.290 | 0.492 |
| experiment3_verse_vs_chorus | Billboard | LTM+ | b0 | 2119 | 118 | 2.100 [1.936, 2.264] | 0.083 | < .001 |
| experiment3_verse_vs_chorus | Billboard | LTM+ | b1 | 2119 | 118 | 0.216 [0.144, 0.288] | 0.036 | < .001 |
| experiment3_verse_vs_chorus | Billboard | LTM+ | b2 | 2119 | 118 | 0.311 [0.080, 0.543] | 0.117 | 0.009 |
| experiment3_verse_vs_chorus | Billboard | LTM+ | b3 | 2119 | 118 | -0.082 [-0.174, 0.010] | 0.046 | 0.079 |
| experiment3_verse_vs_chorus | Billboard | LTM+ | b4 | 2119 | 118 | -0.176 [-0.209, -0.144] | 0.016 | < .001 |
| experiment3_verse_vs_chorus | Billboard | LTM+ | b5 | 2119 | 118 | -0.036 [-0.051, -0.020] | 0.008 | < .001 |
| experiment3_verse_vs_chorus | Billboard | LTM+ | b6 | 2119 | 118 | -1.304 [-1.645, -0.963] | 0.172 | < .001 |
| experiment3_verse_vs_chorus | Billboard | LTM+ | b7 | 2119 | 118 | -0.201 [-0.992, 0.591] | 0.400 | 0.617 |
| experiment3_verse_vs_chorus | Billboard | BOTH+ | b0 | 2119 | 118 | 1.611 [1.447, 1.775] | 0.083 | < .001 |
| experiment3_verse_vs_chorus | Billboard | BOTH+ | b1 | 2119 | 118 | 0.149 [0.088, 0.209] | 0.031 | < .001 |
| experiment3_verse_vs_chorus | Billboard | BOTH+ | b2 | 2119 | 118 | 0.120 [-0.104, 0.345] | 0.113 | 0.291 |
| experiment3_verse_vs_chorus | Billboard | BOTH+ | b3 | 2119 | 118 | -0.075 [-0.152, 0.002] | 0.039 | 0.057 |
| experiment3_verse_vs_chorus | Billboard | BOTH+ | b4 | 2119 | 118 | -0.153 [-0.183, -0.123] | 0.015 | < .001 |
| experiment3_verse_vs_chorus | Billboard | BOTH+ | b5 | 2119 | 118 | -0.039 [-0.052, -0.026] | 0.007 | < .001 |
| experiment3_verse_vs_chorus | Billboard | BOTH+ | b6 | 2119 | 118 | -1.713 [-2.057, -1.368] | 0.174 | < .001 |
| experiment3_verse_vs_chorus | Billboard | BOTH+ | b7 | 2119 | 118 | 0.054 [-0.691, 0.799] | 0.376 | 0.886 |
| experiment3_verse_vs_chorus | Billboard | STM | b0 | 2119 | 118 | 1.722 [1.539, 1.905] | 0.092 | < .001 |
| experiment3_verse_vs_chorus | Billboard | STM | b1 | 2119 | 118 | 0.080 [0.035, 0.125] | 0.023 | < .001 |
| experiment3_verse_vs_chorus | Billboard | STM | b2 | 2119 | 118 | -0.168 [-0.414, 0.079] | 0.125 | 0.181 |
| experiment3_verse_vs_chorus | Billboard | STM | b3 | 2119 | 118 | -0.040 [-0.096, 0.016] | 0.028 | 0.156 |
| experiment3_verse_vs_chorus | Billboard | STM | b4 | 2119 | 118 | -0.108 [-0.138, -0.078] | 0.015 | < .001 |
| experiment3_verse_vs_chorus | Billboard | STM | b5 | 2119 | 118 | -0.024 [-0.034, -0.014] | 0.005 | < .001 |
| experiment3_verse_vs_chorus | Billboard | STM | b6 | 2119 | 118 | -2.141 [-2.545, -1.737] | 0.204 | < .001 |
| experiment3_verse_vs_chorus | Billboard | STM | b7 | 2119 | 118 | 0.063 [-0.702, 0.827] | 0.386 | 0.871 |
| experiment3_verse_vs_chorus | RollingStone | LTM | b0 | 2106 | 117 | 3.174 [3.034, 3.313] | 0.070 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | LTM | b1 | 2106 | 117 | 0.582 [0.449, 0.715] | 0.067 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | LTM | b2 | 2106 | 117 | -0.060 [-0.285, 0.164] | 0.113 | 0.594 |
| experiment3_verse_vs_chorus | RollingStone | LTM | b3 | 2106 | 117 | -0.148 [-0.324, 0.027] | 0.088 | 0.096 |
| experiment3_verse_vs_chorus | RollingStone | LTM | b4 | 2106 | 117 | -0.027 [-0.060, 0.006] | 0.017 | 0.107 |
| experiment3_verse_vs_chorus | RollingStone | LTM | b5 | 2106 | 117 | -0.037 [-0.062, -0.011] | 0.013 | 0.005 |
| experiment3_verse_vs_chorus | RollingStone | LTM | b6 | 2106 | 117 | -0.473 [-0.767, -0.179] | 0.148 | 0.002 |
| experiment3_verse_vs_chorus | RollingStone | LTM | b7 | 2106 | 117 | -0.275 [-1.117, 0.567] | 0.425 | 0.519 |
| experiment3_verse_vs_chorus | RollingStone | LTM+ | b0 | 2106 | 117 | 2.358 [2.200, 2.516] | 0.080 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | LTM+ | b1 | 2106 | 117 | 0.164 [0.084, 0.245] | 0.041 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | LTM+ | b2 | 2106 | 117 | 0.169 [-0.086, 0.423] | 0.129 | 0.192 |
| experiment3_verse_vs_chorus | RollingStone | LTM+ | b3 | 2106 | 117 | 0.076 [-0.048, 0.200] | 0.063 | 0.224 |
| experiment3_verse_vs_chorus | RollingStone | LTM+ | b4 | 2106 | 117 | -0.118 [-0.152, -0.085] | 0.017 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | LTM+ | b5 | 2106 | 117 | -0.053 [-0.074, -0.032] | 0.011 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | LTM+ | b6 | 2106 | 117 | -1.487 [-1.773, -1.201] | 0.145 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | LTM+ | b7 | 2106 | 117 | -0.597 [-1.585, 0.391] | 0.499 | 0.234 |
| experiment3_verse_vs_chorus | RollingStone | BOTH+ | b0 | 2106 | 117 | 1.875 [1.715, 2.035] | 0.081 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | BOTH+ | b1 | 2106 | 117 | 0.109 [0.051, 0.166] | 0.029 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | BOTH+ | b2 | 2106 | 117 | 0.011 [-0.234, 0.256] | 0.124 | 0.928 |
| experiment3_verse_vs_chorus | RollingStone | BOTH+ | b3 | 2106 | 117 | 0.007 [-0.072, 0.085] | 0.040 | 0.869 |
| experiment3_verse_vs_chorus | RollingStone | BOTH+ | b4 | 2106 | 117 | -0.115 [-0.144, -0.087] | 0.014 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | BOTH+ | b5 | 2106 | 117 | -0.042 [-0.057, -0.027] | 0.008 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | BOTH+ | b6 | 2106 | 117 | -1.849 [-2.125, -1.572] | 0.140 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | BOTH+ | b7 | 2106 | 117 | -0.383 [-1.321, 0.555] | 0.474 | 0.421 |
| experiment3_verse_vs_chorus | RollingStone | STM | b0 | 2106 | 117 | 1.935 [1.757, 2.113] | 0.090 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | STM | b1 | 2106 | 117 | 0.042 [-0.013, 0.097] | 0.028 | 0.129 |
| experiment3_verse_vs_chorus | RollingStone | STM | b2 | 2106 | 117 | -0.149 [-0.405, 0.106] | 0.129 | 0.249 |
| experiment3_verse_vs_chorus | RollingStone | STM | b3 | 2106 | 117 | -0.016 [-0.078, 0.046] | 0.031 | 0.618 |
| experiment3_verse_vs_chorus | RollingStone | STM | b4 | 2106 | 117 | -0.106 [-0.131, -0.080] | 0.013 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | STM | b5 | 2106 | 117 | -0.020 [-0.029, -0.010] | 0.005 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | STM | b6 | 2106 | 117 | -2.131 [-2.489, -1.773] | 0.181 | < .001 |
| experiment3_verse_vs_chorus | RollingStone | STM | b7 | 2106 | 117 | -0.325 [-1.251, 0.602] | 0.468 | 0.489 |