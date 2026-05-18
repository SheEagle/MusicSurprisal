# Harmony-Conditioned Cpitch IC

The models use only cpitch and chord. Section labels are used only after IC estimation for grouping and interpretation.

- Songs: 408
- Folds: 5
- Max order: 8
- Alpha: 0.1

## Mean By Section, All Songs

| Section | Cpitch-only IC | Harmony IC | Harmony gain |
|---|---:|---:|---:|
| intro | 4.268 [4.060, 4.477] | 4.492 [4.202, 4.782] | -0.223 [-0.505, 0.058] |
| verse | 4.513 [4.451, 4.575] | 4.496 [4.404, 4.587] | 0.017 [-0.081, 0.116] |
| pre_chorus | 4.502 [4.286, 4.717] | 4.325 [3.956, 4.694] | 0.177 [-0.281, 0.634] |
| chorus | 4.538 [4.464, 4.612] | 4.407 [4.308, 4.505] | 0.131 [0.034, 0.229] |
| bridge | 4.538 [4.418, 4.657] | 4.643 [4.420, 4.866] | -0.105 [-0.324, 0.114] |
| outro | 4.578 [4.435, 4.721] | 4.373 [4.195, 4.552] | 0.205 [0.022, 0.388] |

## Bridge Contrasts

| Contrast | Metric | N | Difference [95% CI] | p |
|---|---|---:|---:|---:|
| bridge_minus_verse | ic_cpitch_only | 121 | 0.010 [-0.125, 0.144] | 0.886 |
| bridge_minus_verse | ic_harmony | 121 | 0.070 [-0.122, 0.263] | 0.471 |
| bridge_minus_verse | harmony_gain | 121 | -0.061 [-0.274, 0.153] | 0.576 |
| bridge_minus_chorus | ic_cpitch_only | 91 | -0.046 [-0.200, 0.108] | 0.554 |
| bridge_minus_chorus | ic_harmony | 91 | 0.168 [-0.076, 0.413] | 0.175 |
| bridge_minus_chorus | harmony_gain | 91 | -0.215 [-0.441, 0.012] | 0.063 |

## Return Effects

Positive values mean IC/gain decreased from first to second occurrence.

| Section | Metric | N | First - second [95% CI] | p |
|---|---|---:|---:|---:|
| verse | ic_cpitch_only | 314 | -0.119 [-0.179, -0.058] | <.001 |
| verse | ic_harmony | 314 | 0.005 [-0.053, 0.063] | 0.859 |
| verse | harmony_gain | 314 | -0.124 [-0.193, -0.055] | <.001 |
| chorus | ic_cpitch_only | 269 | -0.063 [-0.116, -0.010] | 0.021 |
| chorus | ic_harmony | 269 | -0.034 [-0.098, 0.030] | 0.293 |
| chorus | harmony_gain | 269 | -0.028 [-0.095, 0.038] | 0.398 |
| bridge | ic_cpitch_only | 55 | 0.066 [-0.044, 0.175] | 0.236 |
| bridge | ic_harmony | 55 | 0.186 [-0.093, 0.466] | 0.187 |
| bridge | harmony_gain | 55 | -0.121 [-0.370, 0.128] | 0.335 |

## Headline

Bridge harmony gain is -0.105 [-0.324, 0.114], chorus harmony gain is 0.131 [0.034, 0.229]; bridge-minus-chorus gain difference is -0.215 bits, p = 0.063.