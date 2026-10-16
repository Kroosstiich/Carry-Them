#Requires -Version 5.1
<#
Builds Carry Them into Data\ (the mod folder): compiles the Papyrus scripts, generates CarryThem.esp.
-Deploy also mirrors Data\ into the MO2 mod "CarryThem-dev" (never touches the game folder).
-Package <version> also writes release\CarryThem-<version>.zip: Data\ plus the Papyrus sources.
Local paths: local.paths.ps1 next to this file, or the environment variables below.
#>
param([switch]$Deploy, [string]$Package = "")
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$localPaths = Join-Path $Root "local.paths.ps1"
if (Test-Path $localPaths) { . $localPaths }
foreach ($name in "SKYRIM_PATH", "MO2_MODS_PATH", "PIGGYBACK_SOURCE", "MCM_SOURCE") {
    if (-not [Environment]::GetEnvironmentVariable($name)) { throw "Set $name (or local.paths.ps1)." }
}
$Data = Join-Path $Root "Data"
$Compiler = Join-Path $env:SKYRIM_PATH "Papyrus Compiler\PapyrusCompiler.exe"
$Flags = Join-Path $env:SKYRIM_PATH "Data\Source\Scripts\TESV_Papyrus_Flags.flg"
$Source = Join-Path $Root "Scripts\Source"
$imports = @(
    $Source,
    $env:PIGGYBACK_SOURCE,
    $env:MCM_SOURCE,  # MCM Helper + SkyUI sources, for CT_MCM only (import, never shipped)
    (Join-Path $env:MO2_MODS_PATH "Skyrim Script Extender (SKSE64) DATA\Scripts\Source"),
    (Join-Path $env:SKYRIM_PATH "Data\Source\Scripts")
) -join ";"

# The compiler prints its progress on stderr: only the exit code counts.
$ErrorActionPreference = "Continue"
$out = & $Compiler $Source "-all" "-f=$Flags" "-i=$imports" "-o=$(Join-Path $Data 'Scripts')" "-op" 2>&1
$code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
$out | Where-Object { $_ -match "error|warning|succeeded|failed" } | ForEach-Object { Write-Host "  $_" }
if ($code -ne 0) { throw "Papyrus compilation failed." }

# Published .pex must not carry the user or machine name.
& py -3.12 -I (Join-Path $Root "tools\anonymize_pex.py") (Join-Path $Data "Scripts")
if ($LASTEXITCODE -ne 0) { throw "Anonymizing the .pex files failed." }
& py -3.12 -I (Join-Path $Root "tools\build_plugin.py") $Data
if ($LASTEXITCODE -ne 0) { throw "Generating CarryThem.esp failed." }

if ($Deploy) {
    $target = Join-Path $env:MO2_MODS_PATH "CarryThem-dev"
    # /MIR keeps the dev mod an exact copy of Data\ (removes files deleted here).
    robocopy $Data $target /MIR /NJH /NJS /NDL /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Deploy failed (robocopy $LASTEXITCODE)." }
    Write-Host "Deployed: $target"
}

if ($Package) {
    $stage = Join-Path $env:TEMP "CarryThem-package"
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
    Copy-Item $Data $stage -Recurse
    Copy-Item $Source (Join-Path $stage "Scripts\Source") -Recurse
    $zip = Join-Path $Root "release\CarryThem-$Package.zip"
    New-Item -ItemType Directory -Force (Split-Path $zip) | Out-Null
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip -Force
    Remove-Item $stage -Recurse -Force
    Write-Host "Packaged: $zip"
}
