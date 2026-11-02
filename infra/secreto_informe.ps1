# Guarda en GitHub la clave de bi_reader, el usuario de solo lectura con el que se genera el informe mensual.
# Lee la clave de .env.azure y no la muestra.

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot)

$linea = Get-Content .env.azure | Where-Object { $_ -match '^BA_CLAVE_BI=' } | Select-Object -First 1
($linea -split '=', 2)[1].Trim() | gh secret set BA_BI_PASSWORD
Write-Output 'Listo: BA_BI_PASSWORD guardado en GitHub.'
