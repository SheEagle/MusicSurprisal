# RQ4 Independent Project Summary

Pair: `jsb_vs_cocochorales_test1`

Human source: `jsb`

AI source: `cocochorales`

## Framing

This project treats surprisal time series as interpretable information-theoretic
features for symbolic AI music detection. The n-gram measurement model is trained
only on human training data, so AI differences are interpreted relative to human
style expectations rather than as artifacts of an AI-trained model.

## Hypothesis Checks

- `variance`: human mean = 5.999, AI mean = 10.774, AI-human = 4.775, Cohen's d = 1.10

- `peak_rate`: human mean = 0.086, AI mean = 0.169, AI-human = 0.083, Cohen's d = 1.36

- `peak_mass`: human mean = 0.083, AI mean = 0.699, AI-human = 0.617, Cohen's d = 1.72

- `smoothness`: human mean = 0.301, AI mean = 0.269, AI-human = -0.032, Cohen's d = -0.58

- `lag1_autocorr`: human mean = 0.133, AI mean = 0.189, AI-human = 0.056, Cohen's d = 0.25

- `max_autocorr_lag2_16`: human mean = 0.338, AI mean = 0.476, AI-human = 0.139, Cohen's d = 0.64

## Classifier

- Accuracy = 0.844
- F1 = 0.846
- AUC = 0.971
- Permutation p-value = 0.001996
- Pieces = 353

## Interpretation Note

For this pair, inspect the effect directions before committing to the original
"AI is smoother" hypothesis. A positive AI-human value for variance, peak rate, or
peak mass means the AI corpus is more volatile or peak-heavy relative to the
human-trained expectation model.
