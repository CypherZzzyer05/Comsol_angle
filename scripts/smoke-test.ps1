param(
    [string]$ComsolRoot = 'D:\Program Files\COMSOL63\Multiphysics',
    [ValidateRange(1, 256)][int]$Cores = 4
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Path (Join-Path $projectRoot 'work\comsol-tmp') -Force | Out-Null
Push-Location -LiteralPath $projectRoot
try {
    $source = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'SmokeTestNumber37.java') -Raw
    $javaRoot = ConvertTo-Json -InputObject ($projectRoot.Replace('\','/')) -Compress
    $replacement = 'private static final String PROJECT_ROOT = ' + $javaRoot + ';'
    $source = [regex]::Replace($source, 'private static final String PROJECT_ROOT = [^;]+;', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacement })
    $runtimeSource = Join-Path $projectRoot 'work\SmokeTestNumber37.java'
    Set-Content -LiteralPath $runtimeSource -Value $source -Encoding utf8
    $class = Join-Path $projectRoot 'work\SmokeTestNumber37.class'
    if (Test-Path -LiteralPath $class) { Remove-Item -LiteralPath $class }
    & (Join-Path $ComsolRoot 'bin\win64\comsolcompile.exe') $runtimeSource
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $class)) { throw 'COMSOL compilation failed.' }
    $console = Join-Path $projectRoot 'validation\smoke-console.txt'
    $log = Join-Path $projectRoot 'validation\smoke.log'
    if (Test-Path -LiteralPath 'validation\smoke-rt.csv') { Remove-Item -LiteralPath 'validation\smoke-rt.csv' }
    if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log }
    & (Join-Path $ComsolRoot 'bin\win64\comsolbatch.exe') -inputfile $class -nosave -np $Cores -tmpdir (Join-Path $projectRoot 'work\comsol-tmp') -batchlog $log 2>&1 | Tee-Object -FilePath $console
    if ($LASTEXITCODE -ne 0 -or !(Select-String -LiteralPath $console -SimpleMatch 'NUMBER37_SMOKE_OK' -Quiet)) { throw "Single-point validation failed; inspect $log" }
    Write-Output 'Single-point validation passed: 1 deg, 1470 nm. Full 505-case sweep remains configured in the source model.'
} finally { Pop-Location }
