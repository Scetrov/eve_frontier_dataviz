<#
.SYNOPSIS
    Sets up a live development link (junction / symlink / copy) of the add-on into the user's Blender addons directory.

.DESCRIPTION
    Creates (by default) a Windows NTFS directory junction from the repository source folder
    (blender_addon\src\addon) into the Blender addons directory so that edits are immediately
    visible without rebuilding a zip.

    Fallback behaviour: If Mode=Symlink fails (permissions / no Developer Mode), it will fall back to a junction.

.PARAMETER BlenderVersion
    Blender major.minor version directory to target (e.g. 4.0, 4.1, 4.5). Default: 4.5

.PARAMETER TargetName
    Folder name to create inside addons directory. Must match packaged folder (eve_frontier_visualizer).

.PARAMETER Mode
    One of: Junction (default), Symlink, Copy

.PARAMETER Force
    Remove any existing destination before creating link/copy.

.EXAMPLE
    pwsh ./dev_setup_blender_link.ps1

.EXAMPLE
    pwsh ./dev_setup_blender_link.ps1 -BlenderVersion 4.5 -Mode Symlink

.EXAMPLE
    pwsh ./dev_setup_blender_link.ps1 -Mode Copy -Force

.NOTES
    After running, enable the add-on in Blender: Edit > Preferences > Add-ons > search "EVE Frontier".
    For code changes: run blender_addon/scripts/dev_reload.py inside Blender to hot-reload modules.
#>
[CmdletBinding()] param(
    [string]$BlenderVersion = '4.5',
    [string]$TargetName = 'eve_frontier_visualizer',
    [ValidateSet('Junction','Symlink','Copy')][string]$Mode = 'Junction',
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err ($msg){ Write-Host "[ERROR] $msg" -ForegroundColor Red }

$repoRoot = Split-Path -Parent $PSCommandPath
$source   = Join-Path $repoRoot 'blender_addon' | Join-Path -ChildPath 'src' | Join-Path -ChildPath 'addon'
if (-not (Test-Path $source)) { Write-Err "Source folder not found: $source"; exit 2 }

$appData = [Environment]::GetFolderPath('ApplicationData')
$addonsRoot = Join-Path $appData "Blender Foundation/Blender/$BlenderVersion/scripts/addons"
$dest = Join-Path $addonsRoot $TargetName

Write-Info "BlenderVersion = $BlenderVersion"
Write-Info "AddonsRoot    = $addonsRoot"
Write-Info "Source        = $source"
Write-Info "Destination   = $dest"
Write-Info "Mode          = $Mode"

if (-not (Test-Path $addonsRoot)) {
    Write-Info "Creating addons directory $addonsRoot"
    New-Item -ItemType Directory -Force -Path $addonsRoot | Out-Null
}

if (Test-Path $dest) {
    if ($Force) {
        Write-Warn "Removing existing destination $dest"
        Remove-Item -Recurse -Force $dest
    } else {
        Write-Err "Destination already exists: $dest (use -Force to replace)"; exit 3
    }
}

switch ($Mode) {
    'Copy' {
        Write-Info "Copying source → destination"
        Copy-Item -Recurse -Force $source $dest
    }
    'Symlink' {
        try {
            Write-Info "Attempting symbolic link"
            New-Item -ItemType SymbolicLink -Path $dest -Target $source | Out-Null
        } catch {
            Write-Warn "Symlink failed ($($_.Exception.Message)). Falling back to junction."
            New-Item -ItemType Junction -Path $dest -Target $source | Out-Null
        }
    }
    Default { # Junction
        Write-Info "Creating junction"
        New-Item -ItemType Junction -Path $dest -Target $source | Out-Null
    }
}

# Validation
if (-not (Test-Path $dest)) { Write-Err "Destination not created"; exit 4 }
if (-not (Test-Path (Join-Path $dest '__init__.py'))) {
    Write-Warn "__init__.py not found under destination; Blender may not register add-on.";
}

# Determine link type (if possible)
try {
    $item = Get-Item $dest -Force -ErrorAction Stop
    if ($item.LinkType) { Write-Info "LinkType: $($item.LinkType)" }
} catch { }

Write-Host "";
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Open Blender $BlenderVersion" -ForegroundColor Green
Write-Host "  2. Edit > Preferences > Add-ons > search 'EVE Frontier'" -ForegroundColor Green
Write-Host "  3. Enable the add-on (set DB path or env EVE_STATIC_DB)" -ForegroundColor Green
Write-Host "  4. Use dev_reload.py after code edits" -ForegroundColor Green

exit 0
