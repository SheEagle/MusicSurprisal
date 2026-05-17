param(
    [switch]$SkipIdyom,
    [string]$Python = "D:/anaconda3/python.exe",
    [string]$Root = "D:/music"
)

$ErrorActionPreference = "Stop"

& $Python "$Root/scripts/build_dcml_events.py" `
  --dcml-dir "$Root/datasets/raw/dcml/dcml_corpora" `
  --output "$Root/data/events_dcml_classical.csv"

& $Python "$Root/scripts/build_dcml_cadence_taxonomy.py" `
  --dcml-dir "$Root/datasets/raw/dcml/dcml_corpora" `
  --output "$Root/output/formal_dcml_jtc_pop909_slms_all_rq/boundary_taxonomy/dcml_boundary_taxonomy.csv"

$db = "$Root/output/idyom_dcml_melody_beethoven_mozart/input/idyom_dcml_melody.sqlite"
& $Python "$Root/scripts/events_to_idyom_sqlite.py" `
  --events "$Root/data/events_dcml_classical.csv" `
  --output $db `
  --dataset-id 9011 `
  --description dcml_melody_beethoven_mozart `
  --ticks-per-quarter 24 `
  --id-column piece_id

if (-not $SkipIdyom) {
  powershell -ExecutionPolicy Bypass -File "$Root/scripts/run_original_idyom.ps1" `
    -Database $db `
    -OutputDir "$Root/output/idyom_dcml_melody_beethoven_mozart/original_lisp_idyom" `
    -DatasetId 9011 `
    -Models ltm+ `
    -K 3 `
    -OrderBound nil
}

$melodyDat = Get-ChildItem "$Root/output/idyom_dcml_melody_beethoven_mozart/original_lisp_idyom" -Filter *.dat | Sort-Object LastWriteTime -Descending | Select-Object -First 1
& $Python "$Root/scripts/summarize_original_idyom_dat.py" `
  --schema melody `
  --events "$Root/data/events_dcml_classical.csv" `
  --output "$Root/output/idyom_dcml_melody_beethoven_mozart/dcml_melody_original_idyom_event_ic.csv" `
  --dat "idyom=$($melodyDat.FullName)"

& $Python "$Root/scripts/classical_cadence_pipeline.py"
