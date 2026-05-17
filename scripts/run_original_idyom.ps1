param(
    [Parameter(Mandatory = $true)][string]$Database,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [Parameter(Mandatory = $true)][int]$DatasetId,
    [string]$Models = "both+",
    [int]$K = 5,
    [string]$OrderBound = "nil",
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
$env:IDYOM_OVERWRITE = "t"

& $Sbcl --load $Quicklisp --load $Runner --quit
