# RQ4 Independent Project Summary

Pair: `maestro_matched_excerpt_vs_music_transformer_sample500`

Human source: `maestro`

AI source: `music_transformer`

## Framing

This project treats surprisal time series as interpretable information-theoretic
features for symbolic AI music detection. The n-gram measurement model is trained
only on human training data, so AI differences are interpreted relative to human
style expectations rather than as artifacts of an AI-trained model.

## Hypothesis Checks

- `variance`: human mean = 5.714, AI mean = 4.383, AI-human = -1.331, Cohen's d = -0.56

- `peak_rate`: human mean = 0.088, AI mean = 0.127, AI-human = 0.039, Cohen's d = 1.32

- `peak_mass`: human mean = 0.047, AI mean = 0.184, AI-human = 0.136, Cohen's d = 1.18

- `smoothness`: human mean = 0.329, AI mean = 0.378, AI-human = 0.049, Cohen's d = 1.31

- `lag1_autocorr`: human mean = 0.204, AI mean = 0.099, AI-human = -0.105, Cohen's d = -0.63

- `max_autocorr_lag2_16`: human mean = 0.165, AI mean = 0.153, AI-human = -0.012, Cohen's d = -0.14

## Classifier

- Accuracy = 0.801
- F1 = 0.769
- AUC = 0.898
- Permutation p-value = 0.000999
- Pieces = 1000

## Interpretation Note

For this pair, inspect the effect directions before committing to the original
"AI is smoother" hypothesis. A positive AI-human value for variance, peak rate, or
peak mass means the AI corpus is more volatile or peak-heavy relative to the
human-trained expectation model.
