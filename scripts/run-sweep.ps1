param(
    [string]$ComsolRoot = 'D:\Program Files\COMSOL63\Multiphysics',
    [ValidateRange(1, 256)][int]$Cores = 4
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$model = Join-Path $projectRoot 'models\NUMBER37_COMSOL63_angle_wavelength.mph'
if (!(Test-Path -LiteralPath $model)) { throw 'Build the sweep model first with build-model.ps1.' }
$results = Join-Path $projectRoot ('results\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $results -ErrorAction Stop | Out-Null
$batch = Join-Path $ComsolRoot 'bin\win64\comsolbatch.exe'
$log = Join-Path $results 'solve.log'
$temporaryFiles = Join-Path $projectRoot 'work\comsol-tmp'
New-Item -ItemType Directory -Path $temporaryFiles -Force | Out-Null
& $batch -inputfile $model -outputfile (Join-Path $results 'NUMBER37_505_solved.mph') -study std_angle -np $Cores -tmpdir $temporaryFiles -batchlog $log
if ($LASTEXITCODE -ne 0) { throw "COMSOL failed; inspect $log" }
if (Select-String -LiteralPath $log -Pattern '/\*+错误|/\*+Error|没有返回所有参数步长' -Quiet) { throw "COMSOL reported a solve error. Inspect $log" }
if (!(Test-Path -LiteralPath (Join-Path $results 'NUMBER37_505_solved.mph'))) { throw "No solved model was saved. Inspect $log" }
Write-Output "COMSOL process finished. Inspect the solve log and saved solution in $results."
