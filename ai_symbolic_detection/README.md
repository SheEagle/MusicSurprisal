# Independent RQ4 Project: Symbolic AI Music Detection with Surprisal Curves

## Core Question

Do AI-generated symbolic pieces show systematic differences in their surprisal time
series, and are those differences strong enough to support interpretable detection?

## Positioning

Most AI music detection work operates on audio. That creates a risk that detectors
learn platform or synthesis artifacts rather than musical structure. This project
instead works in the symbolic domain and uses features derived from a human-trained
n-gram surprisal curve.

The measurement model is trained on human music only. AI pieces are then scored by
the same model, so the resulting features can be interpreted as deviations from
human stylistic expectations.

## Current Implemented Pair

| Pair | Human | AI | AI architecture | Status |
|---|---|---|---|---|
| `jsb_vs_js_fake` | JSB Chorales | JS Fake Chorales | RNN / KS_Chorus | implemented |
| `maestro_matched_excerpt_vs_music_transformer_sample500` | MAESTRO held-out excerpts | Music Transformer | Transformer | matched prototype |
| `jsb_vs_cocochorales_test1` | JSB Chorales | CocoChorales | Coconet | prototype |

## Planned Extension Pairs

| Pair | Human | AI | AI architecture | Notes |
|---|---|---|---|---|
| `maestro_vs_music_transformer` | MAESTRO | Music Transformer samples | Transformer | scale prototype to larger sample |
| `jsb_vs_cocochorales` | JSB Chorales | CocoChorales MIDI / note expression | Coconet + MIDI-DDSP pipeline | scale prototype to more chunks |

## Feature Families

- Level: mean, p90, p95, max.
- Volatility: variance, SD, coefficient of variation, range.
- Peaks: peak rate, peak mass above the human 90th-percentile threshold.
- Local motion: mean absolute first difference, difference SD, smoothness.
- Autocorrelation: lag-1, lag-4, lag-8, max autocorrelation across lag 2-16.
- Distributional shape: surprisal entropy.

## Hypotheses

The original expected pattern is:

- AI has lower variance: too smooth.
- AI has fewer high-surprisal peaks: fewer dramatic moments.
- AI has more regular autocorrelation: more mechanical repetition.

The implemented analysis treats these as testable hypotheses, not assumptions. In
the current JSB vs JS Fake run, the observed direction is the opposite: JS Fake is
more volatile and more peak-heavy under a JSB-trained expectation model.

## Run

JSB vs JS Fake:

```powershell
python scripts\deep_rq4_analysis.py `
  --events data\events_dcml_jtc_all_rq.csv `
  --output output\ai_symbolic_detection\jsb_vs_js_fake `
  --human-source jsb `
  --ai-source js_fake `
  --pair-name jsb_vs_js_fake `
  --permutations 1000
```

MAESTRO vs Music Transformer prototype:

```powershell
python scripts\download_music_transformer_samples.py --count 500 --seed 13
python scripts\build_music_transformer_events.py `
  --midi-dir datasets\raw\music_transformer\a1 `
  --output data\events_music_transformer_a1_sample500.csv `
  --max-files 500
python scripts\prepare_ai_pair_events.py `
  --human-events data\events_all_rq.csv `
  --ai-events data\events_music_transformer_a1_sample500.csv `
  --output data\pairs\maestro_vs_music_transformer_sample500.csv `
  --human-source maestro `
  --ai-source music_transformer `
  --human-max-pieces-per-split 180
python scripts\deep_rq4_analysis.py `
  --events data\pairs\maestro_vs_music_transformer_sample500.csv `
  --output output\ai_symbolic_detection\maestro_vs_music_transformer_sample500 `
  --human-source maestro `
  --ai-source music_transformer `
  --pair-name maestro_vs_music_transformer_sample500
```

For the controlled comparison, use length-matched held-out MAESTRO excerpts:

```powershell
python scripts\prepare_matched_piano_pair.py `
  --maestro-events data\events_all_rq.csv `
  --ai-events data\events_music_transformer_a1_sample500.csv `
  --output data\pairs\maestro_matched_excerpt_vs_music_transformer_sample500.csv `
  --human-train-pieces 180 `
  --max-ai-pieces 500
python scripts\deep_rq4_analysis.py `
  --events data\pairs\maestro_matched_excerpt_vs_music_transformer_sample500.csv `
  --output output\ai_symbolic_detection\maestro_matched_excerpt_vs_music_transformer_sample500 `
  --human-source maestro `
  --ai-source music_transformer `
  --pair-name maestro_matched_excerpt_vs_music_transformer_sample500
```

JSB vs CocoChorales prototype:

```powershell
python scripts\download_cocochorales_note_expression.py --chunks test:1 --extract
python scripts\build_cocochorales_events.py `
  --input-dir datasets\raw\cocochorales_note_expression\extracted `
  --output data\events_cocochorales_test1.csv `
  --max-pieces 200
python scripts\prepare_ai_pair_events.py `
  --human-events data\events_dcml_jtc_all_rq.csv `
  --ai-events data\events_cocochorales_test1.csv `
  --output data\pairs\jsb_vs_cocochorales_test1.csv `
  --human-source jsb `
  --ai-source cocochorales `
  --human-max-pieces-per-split 200
python scripts\deep_rq4_analysis.py `
  --events data\pairs\jsb_vs_cocochorales_test1.csv `
  --output output\ai_symbolic_detection\jsb_vs_cocochorales_test1 `
  --human-source jsb `
  --ai-source cocochorales `
  --pair-name jsb_vs_cocochorales_test1
```

Cross-generator JSB test:

```powershell
python scripts\cross_generator_generalization.py `
  --pairs output\ai_symbolic_detection\jsb_vs_js_fake `
          output\ai_symbolic_detection\jsb_vs_cocochorales_test1 `
  --output output\ai_symbolic_detection\cross_generator_jsb
```

## Outputs

- `rq4_time_series_features.csv`: piece-level interpretable features.
- `rq4_feature_summary.csv`: human vs AI feature summaries.
- `rq4_human_ai_effects.csv`: AI-human differences and Cohen's d.
- `rq4_human_ai_effects.svg`: effect-size visualization.
- `rq4_hypothesis_panel.svg`: compact hypothesis check.
- `rq4_classifier_from_deep_features.json`: classifier metrics.
- `RQ4_PROJECT_SUMMARY.md`: prose summary of the run.

## Current Prototype Results

`jsb_vs_js_fake`:

- Accuracy = 0.980, F1 = 0.987, AUC = 0.992.
- AI is more volatile and peak-heavy than human JSB under a JSB-trained model.

`maestro_matched_excerpt_vs_music_transformer_sample500`:

- Accuracy = 0.801, F1 = 0.769, AUC = 0.898.
- Music Transformer shows lower variance than length-matched MAESTRO excerpts, but higher peak rate,
  higher peak mass, and higher smoothness under the MAESTRO-trained expectation
  model.

`jsb_vs_cocochorales_test1`:

- Accuracy = 0.844, F1 = 0.846, AUC = 0.971.
- CocoChorales is also more volatile and peak-heavy than human JSB in this
  soprano-line prototype.

Cross-generator JSB:

- Train JS Fake -> test CocoChorales: accuracy = 0.703, AUC = 0.928.
- Train CocoChorales -> test JS Fake: accuracy = 0.982, AUC = 0.998.

## Time-Series Parameter Comparison

Run:

```powershell
python scripts\compare_rq4_time_series_parameters.py `
  --pair-dirs output\ai_symbolic_detection\jsb_vs_js_fake `
              output\ai_symbolic_detection\jsb_vs_cocochorales_test1 `
              output\ai_symbolic_detection\maestro_matched_excerpt_vs_music_transformer_sample500 `
  --output output\ai_symbolic_detection\time_series_comparison_matched
```

Outputs:

- `rq4_time_series_parameter_comparison_long.csv`
- `rq4_time_series_effect_size_matrix.csv`
- `rq4_time_series_direction_summary.csv`
- `rq4_time_series_effect_size_heatmap.svg`
- `rq4_core_time_series_parameters.svg`
- `RQ4_TIME_SERIES_PARAMETER_SUMMARY.md`

Current cross-pair pattern:

- `peak_rate` is higher in AI for 3/3 pairs; mean Cohen's d = 2.36.
- `peak_mass` is higher in AI for 3/3 pairs; mean Cohen's d = 2.28.
- `cv` is lower in AI for 3/3 pairs; mean Cohen's d = -1.46.
- Variance and SD are higher for JS Fake and CocoChorales, but not for the
  current Music Transformer sample20 prototype.

Interpretation: the most stable signal is not simply "AI is smoother." Across the
current prototypes, AI tends to generate more or stronger high-surprisal events
relative to the human-trained expectation model, while the coefficient of variation
is lower because the AI curves also have higher baseline surprisal.

## Literature Hook

Bjare, Lattner, and Widmer (2024), *Controlling Surprisal in Music Generation via
Information Content Curve Matching*, support the idea that information-content
curves are musically meaningful because IIC relates to musical properties such as
harmony, rhythm, and note density.

## Interpretation Discipline

Report each pair as corpus-matched symbolic detection, not universal AI music
detection. Cross-generator generalization should be tested only after adding the
Music Transformer and CocoChorales pairs.
