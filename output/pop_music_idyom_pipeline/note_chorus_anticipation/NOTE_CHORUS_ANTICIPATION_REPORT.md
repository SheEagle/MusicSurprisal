# Note-Level Chorus Incipit Anticipation

This analysis asks whether the upcoming C2 opening notes become a more plausible immediate continuation as the preceding section approaches the chorus boundary.

- Eligible songs: 226
- Folds: 5
- Max order: 8
- Incipit length: 4 notes

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

`other_song_c2`: positive from bin 0.1. `shuffled_c2`: positive from bin 0.1. `v2_opening`: no sustained positive advantage.

Interpretation: this is an immediate-start likelihood analysis, not a true future-horizon rollout. It estimates when the C2 incipit becomes compatible with the note-level context before the section begins.