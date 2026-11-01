$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Crea .venv e instala el proyecto siguiendo README.md.'
}
Push-Location -LiteralPath $projectRoot
try {
    $initializationCode = @'
from ari.core.runtime import AriRuntime
from ari.core.settings import Settings
with AriRuntime(Settings.from_environment()):
    pass
'@
    & $pythonPath -c $initializationCode
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo inicializar SQLite.' }
}
finally {
    Pop-Location
}
