Param(
    [string]$Name
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Reading version from pyproject.toml" -ForegroundColor Cyan
$py = Get-Content .\blender_addon\pyproject.toml -Raw
if ($py -match 'version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"') { $version = $Matches[1] } else { throw 'Version not found' }

if (-not $Name) { $Name = "eve_frontier_visualizer-$version.zip" }

Write-Host "Building $Name" -ForegroundColor Green
python blender_addon/scripts/build_addon.py --name $Name

Write-Host "Done -> dist/$Name" -ForegroundColor Green
