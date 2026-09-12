param(
    [string]$ProjectRoot = $PSScriptRoot,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath($ProjectRoot)
$localConfig = Join-Path $project 'config.local.json'
$exampleConfig = Join-Path $project 'config.example.json'

function Test-Python([string]$Path) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    & $Path -c "import sys;raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,13) else 1)" 2>$null
    return $LASTEXITCODE -eq 0
}

function Test-Node([string]$Path) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    & $Path -e "const v=process.versions.node.split('.')[0];process.exit(Number(v)>=18?0:1)" 2>$null
    return $LASTEXITCODE -eq 0
}

function Resolve-ConfiguredPath([object]$Value) {
    if (-not $Value -or -not ("$Value").Trim()) { return '' }
    if ([IO.Path]::IsPathRooted("$Value")) { return [IO.Path]::GetFullPath("$Value") }
    return [IO.Path]::GetFullPath("$Value", $project)
}

function Select-RequiredFile([string]$Title, [string]$Filter) {
    if ($NonInteractive) { return '' }
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        $Title,
        'Research Starter first-run setup',
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
    $dialog = [System.Windows.Forms.OpenFileDialog]::new()
    $dialog.Title = $Title
    $dialog.Filter = $Filter
    $dialog.CheckFileExists = $true
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { return '' }
    return $dialog.FileName
}

if (Test-Path -LiteralPath $localConfig -PathType Leaf) {
    $config = Get-Content -Raw -LiteralPath $localConfig | ConvertFrom-Json
} else {
    if (-not (Test-Path -LiteralPath $exampleConfig -PathType Leaf)) { throw 'config.example.json is missing.' }
    $config = Get-Content -Raw -LiteralPath $exampleConfig | ConvertFrom-Json
    $config.codex_home = Join-Path $env:USERPROFILE '.codex'
}
if (-not $config.PSObject.Properties['node_exe']) { $config | Add-Member -NotePropertyName node_exe -NotePropertyValue '' }
if (-not $config.PSObject.Properties['npm_cmd']) { $config | Add-Member -NotePropertyName npm_cmd -NotePropertyValue '' }

$projectPython = Join-Path $project '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython -PathType Leaf)) {
    $python = Resolve-ConfiguredPath $config.base_python
    $pythonValid = Test-Python -Path $python
    if (-not $pythonValid) {
        $python = ''
        $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($launcher) {
            foreach ($version in @('3.12', '3.11', '3.10')) {
                $candidate = & ($launcher.Source) "-$version" -c "import sys;print(sys.executable)" 2>$null
                $candidateValid = Test-Python -Path $candidate
                if ($candidateValid) { $python = ("$candidate").Trim(); break }
            }
        }
    }
    $pythonValid = Test-Python -Path $python
    if (-not $pythonValid) {
        foreach ($command in @(Get-Command python.exe -All -ErrorAction SilentlyContinue)) {
            $candidateValid = Test-Python -Path $command.Source
            if ($candidateValid) { $python = $command.Source; break }
        }
    }
    $pythonValid = Test-Python -Path $python
    while (-not $pythonValid) {
        $python = Select-RequiredFile 'Select python.exe from an existing Python 3.10, 3.11, or 3.12 installation. Project packages will be installed only in this project private .venv.' 'Python (python.exe)|python.exe'
        if (-not $python) { throw 'First-run setup cancelled: no compatible Python was selected.' }
        $pythonValid = Test-Python -Path $python
    }
    $config.base_python = $python
}

$requiredNodeAsset = Join-Path $project 'node_modules\pptxgenjs\package.json'
if (-not (Test-Path -LiteralPath $requiredNodeAsset -PathType Leaf)) {
    $node = Resolve-ConfiguredPath $config.node_exe
    $nodeValid = Test-Node -Path $node
    if (-not $nodeValid) {
        $command = Get-Command node.exe -ErrorAction SilentlyContinue
        if ($command) {
            $candidateValid = Test-Node -Path $command.Source
            if ($candidateValid) { $node = $command.Source }
        }
    }
    $nodeValid = Test-Node -Path $node
    while (-not $nodeValid) {
        $node = Select-RequiredFile 'Select node.exe from Node.js 18 or newer. It is used only for project-level Node dependencies.' 'Node.js (node.exe)|node.exe'
        if (-not $node) { throw 'First-run setup cancelled: no compatible Node.js was selected.' }
        $nodeValid = Test-Node -Path $node
    }
    $npm = Resolve-ConfiguredPath $config.npm_cmd
    if (-not (Test-Path -LiteralPath $npm -PathType Leaf)) {
        $besideNode = Join-Path (Split-Path $node -Parent) 'npm.cmd'
        if (Test-Path -LiteralPath $besideNode -PathType Leaf) { $npm = $besideNode }
    }
    if (-not (Test-Path -LiteralPath $npm -PathType Leaf)) {
        $command = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if ($command) { $npm = $command.Source }
    }
    while (-not (Test-Path -LiteralPath $npm -PathType Leaf)) {
        $npm = Select-RequiredFile 'Select npm.cmd from the same Node.js installation.' 'npm command (npm.cmd)|npm.cmd'
        if (-not $npm) { throw 'First-run setup cancelled: npm.cmd was not selected.' }
    }
    $config.node_exe = $node
    $config.npm_cmd = $npm
}

$temporary = "$localConfig.writing"
$config | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding utf8
Get-Content -Raw -LiteralPath $temporary | ConvertFrom-Json | Out-Null
Move-Item -Force -LiteralPath $temporary -Destination $localConfig
Write-Output 'Research Starter startup prerequisites are configured.'
