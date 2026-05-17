param(
    [switch]$SkipIdyom,
    [string]$Python = "D:/anaconda3/python.exe",
    [string]$Root = "D:/music"
)

$ErrorActionPreference = "Stop"

& $Python "$Root/scripts/build_cocopops_events.py" `
  --cocopops-dir "$Root/datasets/raw/CoCoPops" `
  --output "$Root/data/events_cocopops_pop.csv"

$models = @(
  @{ Name = "ltm_plus"; Dataset = 9101; Model = "ltm+"; Out = "$Root/output/idyom_cocopops_melody/ltm_plus/original_lisp_idyom" },
  @{ Name = "both_plus"; Dataset = 9102; Model = "both+"; Out = "$Root/output/idyom_cocopops_melody/both_plus/original_lisp_idyom" },
  @{ Name = "stm_only"; Dataset = 9103; Model = "stm"; Out = "$Root/output/idyom_cocopops_melody/stm_only/original_lisp_idyom" },
  @{ Name = "ltm_plain"; Dataset = 9104; Model = "ltm"; Out = "$Root/output/idyom_cocopops_melody/ltm_plain/original_lisp_idyom" }
)

foreach ($m in $models) {
  $db = "$Root/output/idyom_cocopops_melody/input/$($m.Name).sqlite"
  & $Python "$Root/scripts/events_to_idyom_sqlite.py" `
    --events "$Root/data/events_cocopops_pop.csv" `
    --output $db `
    --dataset-id $m.Dataset `
    --description "cocopops_$($m.Name)" `
    --ticks-per-quarter 96 `
    --id-column piece_id

  if (-not $SkipIdyom) {
    powershell -ExecutionPolicy Bypass -File "$Root/scripts/run_original_idyom.ps1" `
      -Database $db `
      -OutputDir $m.Out `
      -DatasetId $m.Dataset `
      -Models $m.Model `
      -K 5 `
      -OrderBound nil
  }
}

$ltmPlusDat = Get-ChildItem "$Root/output/idyom_cocopops_melody/ltm_plus/original_lisp_idyom" -Filter *.dat | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$bothDat = Get-ChildItem "$Root/output/idyom_cocopops_melody/both_plus/original_lisp_idyom" -Filter *.dat | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$stmDat = Get-ChildItem "$Root/output/idyom_cocopops_melody/stm_only/original_lisp_idyom" -Filter *.dat | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$ltmPlainDat = Get-ChildItem "$Root/output/idyom_cocopops_melody/ltm_plain/original_lisp_idyom" -Filter *.dat | Sort-Object LastWriteTime -Descending | Select-Object -First 1

& $Python "$Root/scripts/summarize_original_idyom_dat.py" `
  --schema pop `
  --events "$Root/data/events_cocopops_pop.csv" `
  --output "$Root/output/idyom_cocopops_melody/cocopops_original_idyom_event_ic.csv" `
  --dat "ltm_plus=$($ltmPlusDat.FullName)" `
  --dat "both_plus=$($bothDat.FullName)" `
  --dat "stm_only=$($stmDat.FullName)"

& $Python "$Root/scripts/summarize_original_idyom_dat.py" `
  --schema pop `
  --events "$Root/data/events_cocopops_pop.csv" `
  --output "$Root/output/idyom_cocopops_melody/cocopops_original_idyom_ltm_plain_event_ic.csv" `
  --dat "ltm_plus=$($ltmPlainDat.FullName)"

& $Python "$Root/scripts/build_cocopops_recurrence_windows.py" `
  --events "$Root/output/idyom_cocopops_melody/cocopops_original_idyom_event_ic.csv" `
  --output "$Root/output/idyom_cocopops_melody/cocopops_recurrence_gain_windows.csv"

& $Python "$Root/scripts/pop_music_idyom_pipeline.py"

& $Python "$Root/scripts/pop_section_form_prediction.py" `
  --events "$Root/data/events_cocopops_pop.csv" `
  --output-dir "$Root/output/pop_music_idyom_pipeline/section_form_prediction" `
  --folds 5 `
  --max-order 4 `
  --alpha 0.1

& $Python "$Root/scripts/pop_note_chorus_anticipation.py" `
  --events "$Root/data/events_cocopops_pop.csv" `
  --output-dir "$Root/output/pop_music_idyom_pipeline/note_chorus_anticipation" `
  --folds 5 `
  --max-order 8 `
  --alpha 0.1 `
  --incipit-notes 4

& $Python "$Root/scripts/pop_monte_carlo_future_horizon.py" `
  --events "$Root/data/events_cocopops_pop.csv" `
  --output-dir "$Root/output/pop_music_idyom_pipeline/monte_carlo_short_horizon" `
  --folds 5 `
  --max-order 8 `
  --alpha 0.1 `
  --incipit-notes 4 `
  --rollouts 100 `
  --horizons 1,2,4,8
