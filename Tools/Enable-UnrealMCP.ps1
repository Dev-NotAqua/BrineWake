param(
  [Parameter(Mandatory=$true)]
  [string]$ProjectPath
)

# Enable-UnrealMCP.ps1 - Enables official Unreal MCP (UE 5.8+) in a .uproject
# Usage: .\Enable-UnrealMCP.ps1 -ProjectPath "C:\Path\To\MyGame.uproject"

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ProjectPath)) { throw "Project file not found: $ProjectPath" }
if ([IO.Path]::GetExtension($ProjectPath) -ne ".uproject") { throw "Not a .uproject file: $ProjectPath" }

$json = Get-Content $ProjectPath -Raw | ConvertFrom-Json
if (-not $json.Plugins) {
  $json | Add-Member -MemberType NoteProperty -Name Plugins -Value @()
}

function Ensure-Plugin($name) {
  $existing = $json.Plugins | Where-Object { $_.Name -eq $name }
  if (-not $existing) {
    $json.Plugins += [PSCustomObject]@{ Name = $name; Enabled = $true }
    Write-Host "Added plugin: $name"
  } else {
    $existing.Enabled = $true
    Write-Host "Enabled plugin: $name"
  }
}

Ensure-Plugin "ModelContextProtocol"
Ensure-Plugin "AllToolsets"

$json | ConvertTo-Json -Depth 10 | Set-Content $ProjectPath -Encoding UTF8
Write-Host "Patched: $ProjectPath"

# Enable AutoStart: UModelContextProtocolSettings is config=EditorPerProjectUserSettings
$projDir = Split-Path $ProjectPath -Parent
$configDir = Join-Path $projDir "Config"
$configFile = Join-Path $configDir "DefaultEditorPerProjectUserSettings.ini"
$section = "[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]"
$desired = @(
  $section,
  "ServerPortNumber=8000",
  "ServerUrlPath=/mcp",
  "bAutoStartServer=True",
  "bEnableToolSearch=True"
)

if (-not (Test-Path $configDir)) { New-Item -ItemType Directory -Path $configDir | Out-Null }

if (Test-Path $configFile) {
  $content = Get-Content $configFile -Raw
  if ($content -match "\[.?Script/ModelContextProtocolEngine\.ModelContextProtocolSettings\]") {
    Write-Host "Settings section already exists in $configFile - please verify bAutoStartServer=True"
    Write-Host "--- current file ---"
    Get-Content $configFile | Select-String -Pattern "ModelContextProtocol" -Context 0,5
  } else {
    Add-Content $configFile ("`r`n" + ($desired -join "`r`n"))
    Write-Host "Appended MCP settings to $configFile"
  }
} else {
  $desired -join "`r`n" | Set-Content $configFile -Encoding UTF8
  Write-Host "Created $configFile with AutoStart=True"
}

Write-Host ""
Write-Host "Next steps in Unreal Editor:"
Write-Host "1. Open project in UE 5.8+, Edit > Plugins > verify 'Unreal MCP' + 'All Toolsets' are Enabled, restart if prompted."
Write-Host "2. Edit > Editor Preferences > Model Context Protocol > check Auto Start Server (should already be on via ini)."
Write-Host "3. Open console (`) and run: ModelContextProtocol.StartServer  (if not auto-started)"
Write-Host "4. Verify at http://127.0.0.1:8000/mcp in browser/MCP Inspector."
Write-Host "5. In opencode, run: opencode mcp list  (unreal-mcp should show 'connected')"
