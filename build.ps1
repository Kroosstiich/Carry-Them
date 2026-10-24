#Requires -Version 5.1
<#
Builds Carry Them into Data\ (the mod folder): compiles the Papyrus scripts, generates CarryThem.esp and
the optional "CarryThem - Dialogue.esp" and "CarryThem - SkyPrompt.esp".
-Deploy also mirrors Data\ into the MO2 mod "CarryThem-dev" (never touches the game folder).
-Package <version> also writes release\CarryThem-<version>.zip, a FOMOD: Core (Data\ plus the Papyrus
sources) and the Dialogue and SkyPrompt options.
Local paths: local.paths.ps1 next to this file, or the environment variables below.
#>
param([switch]$Deploy, [string]$Package = "", [ValidateSet("en", "fr")][string]$Lang = "en")
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
    (Join-Path $env:MO2_MODS_PATH "SkyPrompt\Scripts\Source"),  # SkyPrompt API, for CT_SkyPrompt only
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
& py -3.12 -I (Join-Path $Root "tools\build_plugin.py") $Data $Lang
if ($LASTEXITCODE -ne 0) { throw "Generating CarryThem.esp failed." }

if ($Deploy) {
    $target = Join-Path $env:MO2_MODS_PATH "CarryThem-dev"
    # /MIR keeps the dev mod an exact copy of Data\ (removes files deleted here).
    robocopy $Data $target /MIR /NJH /NJS /NDL /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Deploy failed (robocopy $LASTEXITCODE)." }
    Write-Host "Deployed: $target"
}

if ($Package) {
    # FOMOD layout: Core (always installed) plus one folder per optional way to pick someone up.
    $stage = Join-Path $env:TEMP "CarryThem-package"
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
    $core = Join-Path $stage "Core"
    Copy-Item $Data $core -Recurse
    Copy-Item $Source (Join-Path $core "Scripts\Source") -Recurse
    Copy-Item (Join-Path $Root "fomod") (Join-Path $stage "fomod") -Recurse
    # English in Core whatever -Lang; the French texts go to "<part> French" folders, installed on top.
    $generator = Join-Path $Root "tools\build_plugin.py"
    & py -3.12 -I $generator $core en | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Generating the English plugins failed." }
    $french = Join-Path $stage "French"
    & py -3.12 -I $generator $french fr | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Generating the French plugins failed." }
    foreach ($pair in @(@("Core French", "CarryThem.esp"), @("Core French", "Interface"),
                        @("Dialogue French", "CarryThem - Dialogue.esp"), @("SkyPrompt French", "CarryThem - SkyPrompt.esp"))) {
        $dir = Join-Path $stage $pair[0]
        New-Item -ItemType Directory -Force $dir | Out-Null
        Move-Item (Join-Path $french $pair[1]) $dir
    }
    Remove-Item $french -Recurse -Force
    $optional = @{
        "Dialogue"  = @("CarryThem - Dialogue.esp", "SEQ\CarryThem - Dialogue.seq",
                        "Scripts\CT_TIF_Carry.pex", "Scripts\Source\CT_TIF_Carry.psc")
        "SkyPrompt" = @("CarryThem - SkyPrompt.esp", "Scripts\CT_SkyPrompt.pex", "Scripts\CT_SkyPromptPlayer.pex",
                        "Scripts\Source\CT_SkyPrompt.psc", "Scripts\Source\CT_SkyPromptPlayer.psc")
    }
    foreach ($part in $optional.Keys) {
        foreach ($file in $optional[$part]) {
            $target = Join-Path (Join-Path $stage $part) $file
            New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
            Move-Item (Join-Path $core $file) $target
        }
    }
    Remove-Item (Join-Path $core "SEQ")  # empty once the dialogue part took its file
    $zip = Join-Path $Root "release\CarryThem-$Package.zip"
    New-Item -ItemType Directory -Force (Split-Path $zip) | Out-Null
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip -Force
    Remove-Item $stage -Recurse -Force
    Write-Host "Packaged: $zip"
}
