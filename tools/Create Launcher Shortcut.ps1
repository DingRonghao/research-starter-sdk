param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($ProjectRoot)
$launcher = Join-Path $root 'Start Research Starter.cmd'
$icon = Join-Path $root 'assets\app-icon.ico'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw "Launcher is missing: $launcher" }
if (-not (Test-Path -LiteralPath $icon -PathType Leaf)) { throw "Icon is missing: $icon" }

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $root 'Research Starter.lnk'))
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $root
$shortcut.IconLocation = "$icon,0"
$shortcut.Description = 'Start Research Starter'
$shortcut.WindowStyle = 7
$shortcut.Save()
