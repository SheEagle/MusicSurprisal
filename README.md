# Music Surprisal Pipeline

This repository contains the current analysis pipeline for the symbolic-music
surprisal project. The code is organized around one shared measurement idea:
train n-gram models on symbolic event sequences, convert every piece into a
surprisal time series, then compare time-series structure across research
questions.

The current project scope is:

- **RQ1/RQ2:** classical vs jazz, plus within-DCML Classical vs Romantic.
- **RQ3:** harmony as a distributional modulator of melody-only surprisal.
- **RQ4:** human vs AI symbolic music detection and time-series explanation.

Old exploratory scripts that depended on unsuccessful harmony-conditioned
n-gram tests have been removed. The retained RQ3 version does not ask whether
adding raw chord labels lowers surprisal; it asks whether melody surprisal
differs systematically across harmonic functions and chord-tone status.

## Code Layout

### Core package: `music_surprisal/`

- `ngram.py`  
  Additive-smoothed n-gram model with backoff. This is the main measurement
  tool used across RQs.

- `data.py`  
  Shared event dataclass, CSV reading/writing, tokenization helpers, and
  piece-level grouping utilities.

- `harmony_labels.py`  
  Compact Roman-numeral simplification. It maps detailed DCML labels into
  `T/D/S/other` and `degree:quality` labels.

- `stats.py`, `analysis.py`, `cli.py`  
  General analysis helpers and the older CLI interface. The main paper runs
  currently use the scripts below because they expose more time-series outputs.

### Data builders: `scripts/build_*.py`

- `build_dcml_events.py`  
  Converts DCML expanded/notes tables into `data/events_dcml_classical.csv`.
  It extracts a top-line melodic event per onset, chord label, split, and
  boundary flag.

- `build_jtc_events.py`  
  Converts the JTC jazz corpus into normalized event rows.

- `build_cocochorales_events.py`, `build_music_transformer_events.py`  
  Convert AI symbolic corpora into the same event-table format.

- `build_events.py`  
  Legacy combined builder for MAESTRO, WJazzD, JSB, and JS Fake Chorales. Keep
  it only when rebuilding the broad combined event file.

- `prepare_ai_pair_events.py`, `prepare_matched_piano_pair.py`  
  Create matched human-vs-AI event tables for RQ4.

### Main analyses: `scripts/*analysis.py`

- `rq1_rq2_time_series_analysis.py`  
  Main classical-vs-jazz RQ1/RQ2 analysis. It uses surprisal time-series
  features, normalized curve profiles, local variance, entropy-rate features,
  boundary alignment, unigram baselines, and shuffled baselines.

- `dcml_period_time_series_analysis.py`  
  Within-DCML Classical vs Romantic extension. It uses the manual corpus
  grouping requested in the project:
  `ABC`, Beethoven piano sonatas, Mozart piano sonatas as Classical; Chopin,
  Dvořák, Grieg, Liszt, Medtner, Schumann, and Tchaikovsky as Romantic.

- `dcml_period_rq3_distribution_analysis.py`  
  Current RQ3. It keeps melody-only n-gram surprisal fixed, then asks:
  do `T/D/S/other` harmonic functions have different surprisal distributions?
  Are chord tones and non-chord tones different? How much mutual information
  exists between pitch class and harmonic function?

- `rq4_ai_detection_analysis.py`  
  Main RQ4 human-vs-AI feature extraction and classification analysis using
  human-trained surprisal time series.

- `rq4_curve_shape_analysis.py`  
  RQ4 shape analysis: normalized surprisal profiles, local variance profiles,
  run lengths, change points, and sequence-dependency features.

- `rq4_special_position_analysis.py`  
  RQ4 special-position analysis: whether human and AI surprisal curves align
  differently with boundaries, starts, endings, peaks, and local changes.

- `rq4_bidirectional_expectation_analysis.py`  
  Tests whether the asymmetry also holds in reverse: human-trained models
  listening to AI vs AI-trained models listening to humans.

- `cross_generator_generalization.py`  
  RQ4 application layer: train/test across different AI generators to estimate
  whether surprisal features generalize beyond one generator.

- `compare_rq4_time_series_parameters.py`  
  Collects RQ4 time-series effects across matched human-vs-AI pairs.

- `run_formal_experiment.py`  
  Shared formal runner and utility source, including `load_events`.

## Event Table Format

All analyses expect one row per musical event:

```csv
piece_id,source,genre,is_ai,split,onset,pitch,duration,chord,boundary
```

- `piece_id`: unique piece identifier.
- `source`: corpus name, for example `dcml`, `jtc`, `jsb`, `js_fake`.
- `genre`: analysis group, for example `classical`, `jazz`, `classical_period`.
- `is_ai`: `0` for human, `1` for AI.
- `split`: `train`, `valid`, or `test`.
- `onset`: onset position.
- `pitch`: MIDI pitch integer.
- `duration`: event duration.
- `chord`: chord or Roman-numeral label when available.
- `boundary`: `1` for phrase/cadence/structure boundary, otherwise `0`.

## Suggested Run Order

### 1. Rebuild normalized event tables

```powershell
python scripts\build_dcml_events.py
python scripts\build_jtc_events.py
```

Run the AI builders only if those datasets need to be rebuilt:

```powershell
python scripts\build_cocochorales_events.py
python scripts\build_music_transformer_events.py
python scripts\prepare_ai_pair_events.py
python scripts\prepare_matched_piano_pair.py
```

### 2. RQ1/RQ2: classical vs jazz time-series analysis

```powershell
python scripts\rq1_rq2_time_series_analysis.py
```

Main output:

```text
output/formal_dcml_jtc_all_rq/rq1_rq2_time_series/
```

### 3. RQ1/RQ2 extension: Classical vs Romantic inside DCML

```powershell
python scripts\dcml_period_time_series_analysis.py
```

Main output:

```text
output/formal_dcml_jtc_all_rq/dcml_period_time_series/
```

### 4. RQ3: harmony-function distribution analysis

```powershell
python scripts\dcml_period_rq3_distribution_analysis.py
```

Main output:

```text
output/formal_dcml_jtc_all_rq/dcml_period_rq3_distribution/
```

This is now the primary RQ3 analysis. The previous direct
`melody+harmony-conditioned` n-gram attempt was removed because raw chord labels
created severe sparsity and answered the wrong question.

### 5. RQ4: human vs AI analysis

Run the main detection/time-series feature analysis for each matched pair, then
run the shape and special-position scripts on the same pair table.

Example pattern:

```powershell
python scripts\rq4_ai_detection_analysis.py --events data\pairs\jsb_vs_cocochorales_test1.csv --human-source jsb --ai-source cocochorales --output output\ai_symbolic_detection\jsb_vs_cocochorales_test1
python scripts\rq4_curve_shape_analysis.py --events data\pairs\jsb_vs_cocochorales_test1.csv --human-source jsb --ai-source cocochorales --pair-name jsb_vs_cocochorales_test1 --output output\ai_symbolic_detection\jsb_vs_cocochorales_test1\curve_shape
python scripts\rq4_special_position_analysis.py --events data\pairs\jsb_vs_cocochorales_test1.csv --human-source jsb --ai-source cocochorales --pair-name jsb_vs_cocochorales_test1 --output output\ai_symbolic_detection\jsb_vs_cocochorales_test1\special_positions
```

Use the same pattern for JS Fake Chorales and the matched
MAESTRO-vs-Music-Transformer pair.

## Current Interpretation Strategy

- **RQ1:** emphasize time-series structure over raw mean surprisal. Mean
  differences are reported with coverage/OOV caveats; normalized volatility,
  entropy rate, curve range, and profile shape are the stronger claims.

- **RQ2:** test whether surprisal curves differ near annotated phrase/cadence
  boundaries. The question is not “must surprisal rise,” but whether the local
  curve around special positions is systematically different from non-boundary
  regions and baselines.

- **RQ3:** test whether harmony function modulates melody-only surprisal. This
  avoids conditioning the n-gram on sparse raw chord labels.

- **RQ4:** treat surprisal time series as interpretable symbolic features for
  AI-vs-human comparison. Report both descriptive differences and classifier
  performance, with matched-pair and cross-generator caveats.
