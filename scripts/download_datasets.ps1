param(
    [string]$Root = "datasets\raw",
    [switch]$SkipExtract,
    [switch]$IncludePop,
    [string[]]$DatasetNames = @()
)

$ErrorActionPreference = "Stop"

$rootPath = Resolve-Path -LiteralPath "." | ForEach-Object {
    Join-Path -Path $_.Path -ChildPath $Root
}
$archivePath = Join-Path -Path $rootPath -ChildPath "archives"
New-Item -ItemType Directory -Force -Path $archivePath | Out-Null

$datasets = @(
    @{
        Name = "maestro-v3.0.0-midi";
        Url = "https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-midi.zip";
        File = "maestro-v3.0.0-midi.zip";
        ExtractTo = "maestro-v3.0.0-midi"
    },
    @{
        Name = "wjazzd-db";
        Url = "https://jazzomat.hfm-weimar.de/download/downloads/wjazzd.db";
        File = "wjazzd.db";
        ExtractTo = $null
    },
    @{
        Name = "wjazzd-unquantized-midi";
        Url = "https://jazzomat.hfm-weimar.de/download/downloads/RELEASE2.0_mid_unquant.zip";
        File = "wjazzd-unquantized-midi.zip";
        ExtractTo = "wjazzd-unquantized-midi"
    },
    @{
        Name = "js-fakes";
        Url = "https://github.com/omarperacha/js-fakes/archive/refs/heads/main.zip";
        File = "js-fakes-main.zip";
        ExtractTo = "js-fakes"
    }
)

if ($IncludePop) {
    $datasets += @{
        Name = "pop909";
        Url = "https://github.com/music-x-lab/POP909-Dataset/archive/refs/heads/master.zip";
        File = "POP909-Dataset-master.zip";
        ExtractTo = "pop909"
    }
}

if ($DatasetNames.Count -gt 0) {
    $wanted = @{}
    foreach ($name in $DatasetNames) {
        foreach ($part in ($name -split ",")) {
            if ($part.Trim()) {
                $wanted[$part.Trim()] = $true
            }
        }
    }
    $datasets = @($datasets | Where-Object { $wanted.ContainsKey($_.Name) })
    if ($datasets.Count -eq 0) {
        throw "No matching datasets selected. Known names: maestro-v3.0.0-midi, wjazzd-db, wjazzd-unquantized-midi, js-fakes, pop909"
    }
}

function Test-ZipArchive {
    param([string]$Path)
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
        $zip.Dispose()
        return $true
    } catch {
        return $false
    }
}

foreach ($dataset in $datasets) {
    $destination = Join-Path -Path $archivePath -ChildPath $dataset.File
    $isZip = [System.IO.Path]::GetExtension($destination).ToLowerInvariant() -eq ".zip"

    if (Test-Path -LiteralPath $destination) {
        if ($isZip -and -not (Test-ZipArchive -Path $destination)) {
            Write-Host "Removing incomplete archive: $destination"
            Remove-Item -LiteralPath $destination -Force
        } else {
            Write-Host "Already downloaded: $($dataset.Name) -> $destination"
        }
    }

    if (-not (Test-Path -LiteralPath $destination)) {
        $partial = "$destination.part"
        if (Test-Path -LiteralPath $partial) {
            Remove-Item -LiteralPath $partial -Force
        }
        Write-Host "Downloading: $($dataset.Name)"
        Invoke-WebRequest `
            -Uri $dataset.Url `
            -OutFile $partial `
            -Headers @{ "User-Agent" = "Mozilla/5.0 music-surprisal-pipeline" }
        Move-Item -LiteralPath $partial -Destination $destination -Force
    }

    if ($isZip -and -not (Test-ZipArchive -Path $destination)) {
        throw "Downloaded archive is not a valid zip: $destination"
    }

    if (-not $SkipExtract -and $dataset.ExtractTo) {
        $extractDestination = Join-Path -Path $rootPath -ChildPath $dataset.ExtractTo
        if (Test-Path -LiteralPath $extractDestination) {
            Write-Host "Already extracted: $($dataset.Name) -> $extractDestination"
        } else {
            Write-Host "Extracting: $($dataset.Name)"
            New-Item -ItemType Directory -Force -Path $extractDestination | Out-Null
            Expand-Archive -LiteralPath $destination -DestinationPath $extractDestination -Force
        }
    }
}

if (-not $IncludePop) {
    Write-Host "POP909 skipped. Re-run with -IncludePop if you need the pop corpus later."
}

Write-Host "Dataset download complete: $rootPath"
