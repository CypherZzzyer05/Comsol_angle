param(
    [string]$ComsolRoot = 'D:\Program Files\COMSOL63\Multiphysics',
    [ValidateRange(1, 256)][int]$Cores = 4
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $ComsolRoot 'bin\win64'
$compile = Join-Path $bin 'comsolcompile.exe'
$batch = Join-Path $bin 'comsolbatch.exe'
if (!(Test-Path -LiteralPath $compile) -or !(Test-Path -LiteralPath $batch)) {
    throw 'ComsolRoot must point to the COMSOL Multiphysics installation directory.'
}
New-Item -ItemType Directory -Path (Join-Path $projectRoot 'work'), (Join-Path $projectRoot 'validation') -Force | Out-Null
Push-Location -LiteralPath $projectRoot
try {
    $source = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'RebuildNumber37.java') -Raw
    $javaRoot = ConvertTo-Json -InputObject ($projectRoot.Replace('\','/')) -Compress
    $replacement = 'private static final String PROJECT_ROOT = ' + $javaRoot + ';'
    $source = [regex]::Replace($source, 'private static final String PROJECT_ROOT = [^;]+;', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacement })
    $runtimeSource = Join-Path $projectRoot 'work\RebuildNumber37.java'
    Set-Content -LiteralPath $runtimeSource -Value $source -Encoding utf8
    $class = Join-Path $projectRoot 'work\RebuildNumber37.class'
    if (Test-Path -LiteralPath $class) { Remove-Item -LiteralPath $class }
    & $compile $runtimeSource
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $class)) { throw 'COMSOL compilation failed.' }
    $log = Join-Path $projectRoot 'validation\rebuild.log'
    $console = Join-Path $projectRoot 'validation\rebuild-console.txt'
    if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log }
    & $batch -inputfile $class -nosave -np $Cores -batchlog $log 2>&1 | Tee-Object -FilePath $console
    if ($LASTEXITCODE -ne 0 -or !(Select-String -LiteralPath $console -SimpleMatch 'NUMBER37_REBUILD_OK' -Quiet)) {
        throw "Native model rebuild failed; inspect $log"
    }
    Write-Output 'Built models\NUMBER37_COMSOL63_angle_wavelength.mph (505 cases configured, not solved).'
} finally { Pop-Location }
