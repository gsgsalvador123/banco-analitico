# Aplica en Azure las tablas, procedimientos y vistas de sql/. Se puede repetir sin perder datos.
# Usa el administrador de .env.azure y no muestra ninguna clave.

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot)

$e = @{}
Get-Content .env.azure | Where-Object { $_ -match '=' } | ForEach-Object {
  $k, $v = $_ -split '=', 2
  $e[$k] = $v.Trim()
}
$env:PYTHONPATH = 'src'
$env:BA_SQL_SERVER = $e.BA_AZURE_SERVIDOR
$env:BA_SQL_DATABASE = $e.BA_AZURE_BASE
$env:BA_SQL_AUTH = 'sql'
$env:BA_SQL_USER = $e.BA_AZURE_ADMIN
$env:BA_SQL_PASSWORD = $e.BA_AZURE_ADMIN_CLAVE

& .\.venv\Scripts\python.exe -m banco.etl preparar
