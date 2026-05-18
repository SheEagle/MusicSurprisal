param(
    [Parameter(Mandatory = $true)][string]$Database,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [Parameter(Mandatory = $true)][int]$DatasetId,
    [string]$Models = "both+",
    [int]$K = 5,
    [string]$OrderBound = "nil",
    [int]$Detail = 3,
    [string]$TargetViewpoints = "(cpitch)",
    [string]$SourceViewpoints = "(cpitch)",
    [string]$IdyomRoot = "D:/music/output/idyom_work/",
    [string]$IdyomAsdfDir = "D:/music/external/idyom/",
    [string]$ExtraLoad = "",
    [int]$DynamicSpaceSizeMb = 4096,
    [string]$Sbcl = "D:/music/external/sbcl/PFiles/Steel Bank Common Lisp/sbcl.exe",
    [string]$Quicklisp = "D:/music/external/quicklisp/setup.lisp",
    [string]$Runner = "D:/music/scripts/run_original_idyom.lisp"
)

$env:LOCALAPPDATA = "D:/music/external/localappdata"
$env:XDG_CACHE_HOME = "D:/music/external/localappdata/cache"
$env:IDYOM_DB = $Database
$env:IDYOM_OUTPUT_DIR = $OutputDir
$env:IDYOM_DATASET_ID = [string]$DatasetId
$env:IDYOM_MODELS = $Models
$env:IDYOM_K = [string]$K
$env:IDYOM_ORDER_BOUND = $OrderBound
$env:IDYOM_DETAIL = [string]$Detail
$env:IDYOM_TARGET_VIEWPOINTS = $TargetViewpoints
$env:IDYOM_SOURCE_VIEWPOINTS = $SourceViewpoints
$env:IDYOM_ROOT = $IdyomRoot
$env:IDYOM_ASDF_DIR = $IdyomAsdfDir
$env:IDYOM_OVERWRITE = "t"
if ($ExtraLoad -ne "") {
    $env:IDYOM_EXTRA_LOAD = $ExtraLoad
} else {
    Remove-Item Env:IDYOM_EXTRA_LOAD -ErrorAction SilentlyContinue
}

& $Sbcl --dynamic-space-size $DynamicSpaceSizeMb --load $Quicklisp --load $Runner --quit
