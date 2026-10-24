param(
    [ValidateSet('isolated', 'obstacles', 'clutter', 'dense')][string]$Scene = 'clutter',
    [ValidateRange(1, 10000)][int]$Trials = 3,
    [switch]$Headless
)
$ErrorActionPreference = 'Stop'
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Create .venv with Python 3.12 and install requirements.txt first; see README.md.'
}
$projectArgs = @((Join-Path $PSScriptRoot 'clutter_main.py'), '--scene', $Scene, '--trials', "$Trials")
if ($Headless) { $projectArgs += '--headless' }
& $projectPython @projectArgs
exit $LASTEXITCODE
