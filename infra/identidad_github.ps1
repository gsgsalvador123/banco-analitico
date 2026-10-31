# Crea la identidad con la que GitHub Actions abre y cierra el firewall, y guarda los secretos.
# No usa claves de Azure: GitHub se identifica con OIDC y solo desde la rama main.
# Se puede repetir sin duplicar nada.

$ErrorActionPreference = 'Stop'
$az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
Set-Location (Split-Path $PSScriptRoot)

$sub = & $az account show --query id -o tsv
$grupo = "/subscriptions/$sub/resourceGroups/rg-banco-analitico"
$servidor = "$grupo/providers/Microsoft.Sql/servers/ba-sql-gdhi0s"
$nombreRol = 'BA Firewall Runner'
$temporal = New-TemporaryFile

# Rol propio: solo reglas de firewall, sin acceso a datos ni a otros recursos.
if (-not (& $az role definition list --name $nombreRol --scope $grupo --query "[0].name" -o tsv)) {
  @{
    Name = $nombreRol
    Description = 'Solo reglas de firewall del servidor SQL del proyecto'
    Actions = @(
      'Microsoft.Sql/servers/read',
      'Microsoft.Sql/servers/firewallRules/read',
      'Microsoft.Sql/servers/firewallRules/write',
      'Microsoft.Sql/servers/firewallRules/delete'
    )
    NotActions = @()
    AssignableScopes = @($grupo)
  } | ConvertTo-Json | Set-Content $temporal -Encoding ascii
  & $az role definition create --role-definition "@$temporal" --output none
}

$app = & $az ad app list --display-name banco-analitico-github --query "[0].appId" -o tsv
if (-not $app) { $app = & $az ad app create --display-name banco-analitico-github --query appId -o tsv }
if (-not (& $az ad sp list --filter "appId eq '$app'" --query "[0].id" -o tsv)) {
  & $az ad sp create --id $app --output none
}

if (-not (& $az ad app federated-credential list --id $app --query "[?name=='github-main'].name" -o tsv)) {
  @{
    name = 'github-main'
    issuer = 'https://token.actions.githubusercontent.com'
    subject = 'repo:gsgsalvador123/banco-analitico:ref:refs/heads/main'
    audiences = @('api://AzureADTokenExchange')
  } | ConvertTo-Json | Set-Content $temporal -Encoding ascii
  & $az ad app federated-credential create --id $app --parameters "@$temporal" --output none
}
Remove-Item $temporal

# La identidad recién creada tarda unos segundos en verse desde Azure.
Start-Sleep 30
& $az role assignment create --assignee $app --role $nombreRol --scope $servidor --output none

$e = @{}
Get-Content .env.azure | Where-Object { $_ -match '=' } | ForEach-Object {
  $k, $v = $_ -split '=', 2
  $e[$k] = $v.Trim()
}
$app | gh secret set AZURE_CLIENT_ID
& $az account show --query tenantId -o tsv | gh secret set AZURE_TENANT_ID
$sub | gh secret set AZURE_SUBSCRIPTION_ID
$e.BA_AZURE_SERVIDOR | gh secret set BA_SQL_SERVER
$e.BA_AZURE_BASE | gh secret set BA_SQL_DATABASE
'etl_user' | gh secret set BA_SQL_USER
$e.BA_CLAVE_ETL | gh secret set BA_SQL_PASSWORD

Write-Output 'Listo: identidad creada y secretos guardados'
