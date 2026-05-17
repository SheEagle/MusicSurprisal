# Section-Level Formal Prediction

This experiment treats section labels as symbolic events and estimates the IC of formal returns with k-fold cross-validation.

- Songs with section sequences: 396
- Folds: 5
- Max order: 4
- Smoothing alpha: 0.1

The key paired effect is `verse return IC - chorus return IC`; positive values mean the second chorus is more expected than the second verse at the section-transition level.

| Source | Model | N songs | Chorus IC | Verse IC | Verse - chorus IC [95% CI] | p |
|---|---|---:|---:|---:|---:|---:|
| ALL | LTM | 235 | 0.791 | 1.501 | 0.710 [0.551, 0.870] | <.001 |
| ALL | STM | 235 | 2.325 | 2.515 | 0.191 [0.093, 0.289] | <.001 |
| ALL | BOTH | 235 | 0.952 | 1.731 | 0.779 [0.674, 0.885] | <.001 |
| cocopops_billboard | LTM | 118 | 0.809 | 1.640 | 0.831 [0.569, 1.094] | <.001 |
| cocopops_billboard | STM | 118 | 2.381 | 2.523 | 0.142 [-0.018, 0.301] | 0.082 |
| cocopops_billboard | BOTH | 118 | 1.002 | 1.797 | 0.795 [0.619, 0.971] | <.001 |
| cocopops_rollingstone | LTM | 117 | 0.774 | 1.361 | 0.588 [0.406, 0.770] | <.001 |
| cocopops_rollingstone | STM | 117 | 2.267 | 2.508 | 0.240 [0.125, 0.355] | <.001 |
| cocopops_rollingstone | BOTH | 117 | 0.902 | 1.665 | 0.763 [0.644, 0.882] | <.001 |

Outputs:

- `section_return_predictions.csv`: event-level section return predictions.
- `section_return_paired_song_effects.csv`: within-song chorus-return vs verse-return pairs.
- `section_return_summary.csv`: paired t-test summaries.
- `section_return_ic_advantage.svg/png`: compact figure.