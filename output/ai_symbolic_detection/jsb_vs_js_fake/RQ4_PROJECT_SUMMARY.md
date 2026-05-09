# RQ4 Independent Project Summary

Pair: `jsb_vs_js_fake`

Human source: `jsb`

AI source: `js_fake`

## Framing

This project treats surprisal time series as interpretable information-theoretic
features for symbolic AI music detection. The n-gram measurement model is trained
only on human training data, so AI differences are interpreted relative to human
style expectations rather than as artifacts of an AI-trained model.

## Hypothesis Checks

- `variance`: human mean = 5.935, AI mean = 9.971, AI-human = 4.036, Cohen's d = 1.65

- `peak_rate`: human mean = 0.087, AI mean = 0.285, AI-human = 0.198, Cohen's d = 4.51

- `peak_mass`: human mean = 0.079, AI mean = 0.809, AI-human = 0.730, Cohen's d = 4.08

- `smoothness`: human mean = 0.302, AI mean = 0.209, AI-human = -0.093, Cohen's d = -2.71

- `lag1_autocorr`: human mean = 0.132, AI mean = -0.119, AI-human = -0.251, Cohen's d = -1.50

- `max_autocorr_lag2_16`: human mean = 0.337, AI mean = 0.269, AI-human = -0.068, Cohen's d = -0.62

## Classifier

- Accuracy = 0.980
- F1 = 0.987
- AUC = 0.992
- Permutation p-value = 0.000999
- Pieces = 653

## Interpretation Note

For this pair, inspect the effect directions before committing to the original
"AI is smoother" hypothesis. A positive AI-human value for variance, peak rate, or
peak mass means the AI corpus is more volatile or peak-heavy relative to the
human-trained expectation model.
