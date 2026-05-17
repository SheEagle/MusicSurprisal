# Original IDyOM Pipeline

This project keeps the paper-facing analysis in:

- `scripts/pop_music_idyom_pipeline.py`
- `scripts/classical_cadence_pipeline.py`

Those scripts start from event-level CSV files that already contain original
Common Lisp IDyOM IC/entropy values. The missing reproducibility layer is:

```text
project event CSV
-> IDyOM sqlite database
-> original Lisp IDyOM .dat output
-> merged event-level CSV
-> final analysis pipeline
```

## 1. Convert project events to IDyOM sqlite

Popular music melody:

```powershell
python D:/music/scripts/events_to_idyom_sqlite.py `
  --events D:/music/data/events_cocopops_pop.csv `
  --output D:/music/output/idyom_cocopops_melody/input/idyom_cocopops_melody.sqlite `
  --dataset-id 9101 `
  --description cocopops_melody `
  --ticks-per-quarter 96 `
  --id-column piece_id
```

Classical DCML melody:

```powershell
python D:/music/scripts/events_to_idyom_sqlite.py `
  --events D:/music/data/events_dcml_classical.csv `
  --output D:/music/output/idyom_dcml_melody_beethoven_mozart/input/idyom_dcml_melody.sqlite `
  --dataset-id 9011 `
  --description dcml_melody_beethoven_mozart `
  --ticks-per-quarter 24 `
  --id-column piece_id
```

## 2. Run original Lisp IDyOM

The reusable Lisp runner is `scripts/run_original_idyom.lisp`.

The command line is SBCL plus environment variables. Example for CoCoPops
LTM+:

```powershell
$env:LOCALAPPDATA = "D:/music/external/localappdata"
$env:XDG_CACHE_HOME = "D:/music/external/localappdata/cache"
$env:IDYOM_DB = "D:/music/output/idyom_cocopops_melody/input/idyom_cocopops_melody.sqlite"
$env:IDYOM_OUTPUT_DIR = "D:/music/output/idyom_cocopops_melody/ltm_plus/original_lisp_idyom"
$env:IDYOM_DATASET_ID = "9101"
$env:IDYOM_MODELS = "ltm+"
$env:IDYOM_K = "5"
$env:IDYOM_ORDER_BOUND = "nil"
$env:IDYOM_OVERWRITE = "t"
& "D:/music/external/sbcl/PFiles/Steel Bank Common Lisp/sbcl.exe" `
  --load "D:/music/external/quicklisp/setup.lisp" `
  --load "D:/music/scripts/run_original_idyom.lisp" `
  --quit
```

Equivalent wrapper command:

```powershell
powershell -ExecutionPolicy Bypass -File D:/music/scripts/run_original_idyom.ps1 `
  -Database D:/music/output/idyom_cocopops_melody/input/idyom_cocopops_melody.sqlite `
  -OutputDir D:/music/output/idyom_cocopops_melody/ltm_plus/original_lisp_idyom `
  -DatasetId 9101 `
  -Models ltm+ `
  -K 5 `
  -OrderBound nil
```

The actual Lisp call inside the runner is:

```lisp
(idyom:idyom dataset-id
             '(cpitch)
             '(cpitch)
             :models models
             :k k
             :ltmo `(:order-bound ,order-bound)
             :stmo `(:order-bound ,order-bound)
             :texture :melody
             :detail 3
             :output-path output-dir
             :separator ","
             :null-token "NA"
             :information-measure '(:ic :entropy)
             :overwrite overwrite)
```

For the current popular-music analyses, run the same command with:

```text
IDYOM_MODELS=ltm+   IDYOM_DATASET_ID=9101
IDYOM_MODELS=both+  IDYOM_DATASET_ID=9102
IDYOM_MODELS=stm    IDYOM_DATASET_ID=9103
IDYOM_MODELS=ltm    IDYOM_DATASET_ID=9104
```

For order-8 robustness, set:

```text
IDYOM_ORDER_BOUND=8
```

For classical melody, use:

```text
IDYOM_DATASET_ID=9011
IDYOM_K=3
IDYOM_MODELS=ltm+
```

## 3. Convert IDyOM .dat output back to event-level CSV

IDyOM `.dat` files are comma-separated text files. They contain columns such as:

```text
dataset.id, melody.id, note.id, cpitch, cpitch.ic, cpitch.entropy, ic, entropy
```

We merge them back to project events using:

```text
(melody.id, note.id) == (melody_id_1, note_id_1)
```

Popular music combined CSV:

```powershell
python D:/music/scripts/summarize_original_idyom_dat.py `
  --schema pop `
  --events D:/music/data/events_cocopops_pop.csv `
  --output D:/music/output/idyom_cocopops_melody/cocopops_original_idyom_event_ic.csv `
  --dat ltm_plus=D:/music/output/idyom_cocopops_melody/ltm_plus/original_lisp_idyom/<IDYOM_OUTPUT>.dat `
  --dat both_plus=D:/music/output/idyom_cocopops_melody/both_plus/original_lisp_idyom/<IDYOM_OUTPUT>.dat `
  --dat stm_only=D:/music/output/idyom_cocopops_melody/stm_only/original_lisp_idyom/<IDYOM_OUTPUT>.dat
```

Plain LTM CSV:

```powershell
python D:/music/scripts/summarize_original_idyom_dat.py `
  --schema pop `
  --events D:/music/data/events_cocopops_pop.csv `
  --output D:/music/output/idyom_cocopops_melody/cocopops_original_idyom_ltm_plain_event_ic.csv `
  --dat ltm_plus=D:/music/output/idyom_cocopops_melody/ltm_plain/original_lisp_idyom/<IDYOM_OUTPUT>.dat
```

Classical melody CSV:

```powershell
python D:/music/scripts/summarize_original_idyom_dat.py `
  --schema melody `
  --events D:/music/data/events_dcml_classical.csv `
  --output D:/music/output/idyom_dcml_melody_beethoven_mozart/dcml_melody_original_idyom_event_ic.csv `
  --dat idyom=D:/music/output/idyom_dcml_melody_beethoven_mozart/original_lisp_idyom/<IDYOM_OUTPUT>.dat
```

## 4. Run final analysis

End-to-end wrappers are available for the two current paper pipelines.

Popular music, from raw CoCoPops files to final reports:

```powershell
powershell -ExecutionPolicy Bypass -File D:/music/scripts/run_pop_complete_pipeline.ps1
```

Classical melody/cadence analysis, from raw DCML files to final reports:

```powershell
powershell -ExecutionPolicy Bypass -File D:/music/scripts/run_classical_complete_pipeline.ps1
```

Use `-SkipIdyom` only for debugging when the `.dat` files already exist and only
the post-IDyOM conversion/analysis layers need to be regenerated.

Popular music:

```powershell
python D:/music/scripts/pop_music_idyom_pipeline.py
```

Classical cadence:

```powershell
python D:/music/scripts/classical_cadence_pipeline.py
```
