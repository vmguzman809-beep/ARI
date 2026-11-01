$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Crea .venv e instala .[dev] siguiendo README.md.'
}
Push-Location -LiteralPath $projectRoot
try {
    & $pythonPath -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw 'Ruff detecto errores.' }
    & $pythonPath -m ruff format --check .
    if ($LASTEXITCODE -ne 0) { throw 'El formato necesita correcciones.' }
    & $pythonPath -m pytest
    if ($LASTEXITCODE -ne 0) { throw 'Las pruebas fallaron.' }
    & $pythonPath -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Las dependencias son incompatibles.' }
}
finally {
    Pop-Location
}
