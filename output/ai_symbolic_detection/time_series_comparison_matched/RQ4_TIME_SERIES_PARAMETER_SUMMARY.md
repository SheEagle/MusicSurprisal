# RQ4 Time-Series Parameter Comparison

This comparison aggregates the interpretable surprisal time-series parameters
across available AI-vs-human pairs. Effect sizes are Cohen's d for AI minus
human within each matched pair, which is safer than comparing raw values
across different musical styles.

## Main Pattern

- `variance`: AI higher in 2/3 pairs; mean d = 0.73.
- `sd`: AI higher in 2/3 pairs; mean d = 0.71.
- `cv`: AI higher in 0/3 pairs; mean d = -1.40.
- `peak_rate`: AI higher in 3/3 pairs; mean d = 2.40.
- `peak_mass`: AI higher in 3/3 pairs; mean d = 2.33.
- `mean_abs_diff`: AI higher in 2/3 pairs; mean d = 0.63.
- `smoothness`: AI higher in 1/3 pairs; mean d = -0.66.
- `lag1_autocorr`: AI higher in 1/3 pairs; mean d = -0.63.
- `lag4_autocorr`: AI higher in 1/3 pairs; mean d = 0.20.
- `max_autocorr_lag2_16`: AI higher in 1/3 pairs; mean d = -0.04.
- `surprisal_entropy`: AI higher in 1/3 pairs; mean d = -0.63.

## Pair Matrix

### jsb_vs_cocochorales_test1
- `variance`: d = 1.10, AI-human = 4.775
- `sd`: d = 1.09, AI-human = 0.750
- `cv`: d = -1.58, AI-human = -0.131
- `peak_rate`: d = 1.36, AI-human = 0.083
- `peak_mass`: d = 1.72, AI-human = 0.617
- `mean_abs_diff`: d = 0.74, AI-human = 0.477
- `smoothness`: d = -0.58, AI-human = -0.032
- `lag1_autocorr`: d = 0.25, AI-human = 0.056
- `lag4_autocorr`: d = -0.18, AI-human = -0.038
- `max_autocorr_lag2_16`: d = 0.64, AI-human = 0.139
- `surprisal_entropy`: d = -1.36, AI-human = -0.424

### jsb_vs_js_fake
- `variance`: d = 1.65, AI-human = 4.036
- `sd`: d = 1.81, AI-human = 0.729
- `cv`: d = -1.23, AI-human = -0.087
- `peak_rate`: d = 4.51, AI-human = 0.198
- `peak_mass`: d = 4.08, AI-human = 0.730
- `mean_abs_diff`: d = 2.44, AI-human = 1.472
- `smoothness`: d = -2.71, AI-human = -0.093
- `lag1_autocorr`: d = -1.50, AI-human = -0.251
- `lag4_autocorr`: d = 0.88, AI-human = 0.124
- `max_autocorr_lag2_16`: d = -0.62, AI-human = -0.068
- `surprisal_entropy`: d = 1.15, AI-human = 0.190

### maestro_matched_excerpt_vs_music_transformer_sample500
- `variance`: d = -0.56, AI-human = -1.331
- `sd`: d = -0.77, AI-human = -0.349
- `cv`: d = -1.38, AI-human = -0.064
- `peak_rate`: d = 1.32, AI-human = 0.039
- `peak_mass`: d = 1.18, AI-human = 0.136
- `mean_abs_diff`: d = -1.30, AI-human = -0.383
- `smoothness`: d = 1.31, AI-human = 0.049
- `lag1_autocorr`: d = -0.63, AI-human = -0.105
- `lag4_autocorr`: d = -0.10, AI-human = -0.010
- `max_autocorr_lag2_16`: d = -0.14, AI-human = -0.012
- `surprisal_entropy`: d = -1.67, AI-human = -0.587
