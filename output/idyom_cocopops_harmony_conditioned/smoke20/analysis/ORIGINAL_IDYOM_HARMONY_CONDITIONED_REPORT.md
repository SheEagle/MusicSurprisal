# Original IDyOM Harmony-Conditioned Cpitch Smoke Test

This is an original Lisp IDyOM implementation of harmony-conditioned cpitch IC.

Formula:

```text
IC(cpitch | chord, past) ~= IC(chord, cpitch | past) - IC(chord | past)
Harmony gain = IC(cpitch-only) - IC(cpitch | chord)
```

Implementation note: chord and chord+cpitch are encoded as symbolic CPITCH vocabularies before being passed to original IDyOM. Section labels are used only after scoring.

- Event rows scored: 5038
- Songs scored: 20

## Mean By Section

| Section | Cpitch-only IC | Cpitch given chord IC | Harmony gain |
|---|---:|---:|---:|
| intro | 4.108 [3.080, 5.136] | 2.512 [0.733, 4.290] | 1.596 [-0.590, 3.783] |
| verse | 2.794 [2.505, 3.083] | 3.240 [2.577, 3.903] | -0.446 [-1.064, 0.172] |
| pre_chorus | 2.624 [2.527, 2.721] | 1.988 [-8.633, 12.609] | 0.636 [-10.082, 11.354] |
| chorus | 2.731 [2.122, 3.341] | 2.172 [1.389, 2.954] | 0.560 [-0.155, 1.274] |
| bridge | 3.057 [2.086, 4.028] | 3.717 [2.498, 4.936] | -0.660 [-1.276, -0.044] |
| outro | 2.326 [1.668, 2.984] | 2.517 [0.639, 4.396] | -0.191 [-2.022, 1.640] |

## Bridge Contrasts

| Contrast | Metric | N | Difference [95% CI] | p |
|---|---|---:|---:|---:|
| bridge_minus_verse | idyom_ic_cpitch_only | 5 | 0.316 [-1.302, 1.934] | 0.616 |
| bridge_minus_verse | idyom_ic_cpitch_given_chord | 5 | 0.986 [-1.539, 3.511] | 0.339 |
| bridge_minus_verse | idyom_harmony_gain | 5 | -0.669 [-3.043, 1.704] | 0.477 |
| bridge_minus_chorus | idyom_ic_cpitch_only | 5 | 0.047 [-2.035, 2.129] | 0.953 |
| bridge_minus_chorus | idyom_ic_cpitch_given_chord | 5 | 1.348 [0.310, 2.385] | 0.023 |
| bridge_minus_chorus | idyom_harmony_gain | 5 | -1.300 [-3.857, 1.256] | 0.231 |