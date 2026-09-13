param(
    [string]$Version = '1.1.0-internal.2'
)

$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$dist = Join-Path $project 'dist'
$name = "Research-Starter-Windows-$Version"
$stage = Join-Path $dist $name
$archive = Join-Path $dist "$name.zip"
$launcherSource = Join-Path $project 'tools\ResearchStarterLauncher.cs'
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'

if (-not (Test-Path -LiteralPath $compiler -PathType Leaf)) { throw "Windows C# compiler is missing: $compiler" }

foreach ($required in @(
    (Join-Path $project 'runtime\python\python.exe'),
    (Join-Path $project 'runtime\node\node.exe'),
    (Join-Path $project 'node_modules\pptxgenjs\package.json')
)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Bundled release dependency is missing: $required"
    }
}

if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null

& robocopy $project $stage /E /XD .git .runtime .venv runtime node_modules tests tools tmp dist (Join-Path $project 'assets\source') /XF config.local.json .gitignore .gitattributes MIGRATION_BASELINE.md MIGRATION_LOG.md RELEASE_DATA_POLICY.md RESEARCH_STARTER_V0_2_CONSTRUCTION_GUIDE.md UI_UPDATE_20260912.md /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -gt 7) { throw "Application copy failed with robocopy exit code $LASTEXITCODE" }
& $compiler /nologo /target:winexe /reference:System.Windows.Forms.dll "/win32icon:$project\assets\app-icon.ico" "/out:$stage\Research Starter.exe" $launcherSource
if ($LASTEXITCODE -ne 0) { throw "Launcher compilation failed with exit code $LASTEXITCODE" }
& robocopy (Join-Path $project 'runtime') (Join-Path $stage 'runtime') /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -gt 7) { throw "Runtime copy failed with robocopy exit code $LASTEXITCODE" }
& robocopy (Join-Path $project 'node_modules') (Join-Path $stage 'node_modules') /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -gt 7) { throw "Node dependency copy failed with robocopy exit code $LASTEXITCODE" }

Push-Location $dist
try {
    & tar.exe -a -cf "$name.zip" $name
    if ($LASTEXITCODE -ne 0) { throw "Release archive creation failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash
Write-Output "Release: $archive"
Write-Output "SHA256: $hash"
