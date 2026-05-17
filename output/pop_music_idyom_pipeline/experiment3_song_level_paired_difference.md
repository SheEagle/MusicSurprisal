# Experiment 3: Song-Level Paired Difference

Formula:

```text
D_s = mean(IC2_verse_s) - mean(IC2_chorus_s)
D_s = beta0 + beta1*delta_IC1_s + beta2*delta_pitch_similarity_s + beta3*delta_mean_onset_position_s + error_s
```

Positive beta0 means verse has higher second-occurrence IC than chorus; therefore chorus is more predictable.

| Corpus | Model | N songs | Chorus IC2 | Verse IC2 | beta0 verse - chorus [95% CI] | p |
|---|---|---:|---:|---:|---:|---:|
| Billboard | LTM | 118 | 3.306 | 3.309 | 0.003 [-0.152, 0.157] | 0.972 |
| Billboard | LTM+ | 118 | 2.007 | 2.552 | 0.545 [0.385, 0.705] | < .001 |
| Billboard | BOTH+ | 118 | 1.501 | 1.894 | 0.393 [0.237, 0.549] | < .001 |
| Billboard | STM | 118 | 1.571 | 1.760 | 0.189 [0.025, 0.352] | 0.024 |
| RollingStone | LTM | 117 | 3.169 | 3.153 | -0.016 [-0.194, 0.161] | 0.857 |
| RollingStone | LTM+ | 117 | 2.278 | 2.652 | 0.374 [0.184, 0.564] | < .001 |
| RollingStone | BOTH+ | 117 | 1.790 | 2.023 | 0.233 [0.048, 0.418] | 0.014 |
| RollingStone | STM | 117 | 1.829 | 1.929 | 0.100 [-0.095, 0.295] | 0.312 |