param(
    [string]$Version = '1.2.0-internal.1',
    [string]$CertificateThumbprint = '',
    [string]$TimestampUrl = 'http://timestamp.digicert.com',
    [switch]$RequireSignature
)

$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$dist = Join-Path $project 'dist'
$name = "Research-Starter-Windows-$Version"
$stage = Join-Path $dist $name
$archive = Join-Path $dist "$name.zip"
$launcherSource = Join-Path $project 'tools\ResearchStarterLauncher.cs'
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'

function Get-Sha256WithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$LiteralPath,
        [int]$Attempts = 30,
        [int]$DelayMilliseconds = 1000
    )
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            return (Get-FileHash -Algorithm SHA256 -LiteralPath $LiteralPath -ErrorAction Stop).Hash
        } catch {
            if ($attempt -eq $Attempts) {
                throw "Unable to calculate SHA-256 after $Attempts attempts: $LiteralPath. $($_.Exception.Message)"
            }
            Start-Sleep -Milliseconds $DelayMilliseconds
        }
    }
}

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

& robocopy $project $stage /E /XD .git .runtime .venv runtime node_modules Inbox Output tests tools tmp dist (Join-Path $project 'assets\source') /XF "Research Starter.exe" config.local.json .gitignore .gitattributes MIGRATION_BASELINE.md MIGRATION_LOG.md RELEASE_DATA_POLICY.md RELEASE_WORKFLOW.md RESEARCH_STARTER_V0_2_CONSTRUCTION_GUIDE.md UI_UPDATE_20260912.md /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -gt 7) { throw "Application copy failed with robocopy exit code $LASTEXITCODE" }
foreach ($task in @('paper-guide', 'research-note', 'research-slides')) {
    foreach ($area in @('Inbox', 'Output')) {
        $sampleSource = Join-Path $project "$area\$task\public-sample"
        $sampleDestination = Join-Path $stage "$area\$task\public-sample"
        if (-not (Test-Path -LiteralPath $sampleSource -PathType Container)) {
            throw "Required public sample is missing: $sampleSource"
        }
        & robocopy $sampleSource $sampleDestination /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
        if ($LASTEXITCODE -gt 7) { throw "Public sample copy failed with robocopy exit code $LASTEXITCODE" }
    }
}
$releaseTemplateLibrary = Join-Path $stage 'Inbox\Templates'
New-Item -ItemType Directory -Force -Path $releaseTemplateLibrary | Out-Null
$publicTemplateName = '高校通用学术论文汇报模板_31页_版式细化版.pptx'
$publicTemplateSource = Join-Path $project "Inbox\Templates\$publicTemplateName"
if (-not (Test-Path -LiteralPath $publicTemplateSource -PathType Leaf)) {
    throw "Required public PPT template is missing: $publicTemplateSource"
}
Copy-Item -LiteralPath $publicTemplateSource -Destination (Join-Path $releaseTemplateLibrary $publicTemplateName)
& $compiler /nologo /target:winexe /reference:System.Windows.Forms.dll "/win32icon:$project\assets\app-icon.ico" "/out:$stage\Research Starter.exe" $launcherSource
if ($LASTEXITCODE -ne 0) { throw "Launcher compilation failed with exit code $LASTEXITCODE" }
$launcher = Join-Path $stage 'Research Starter.exe'
$thumbprint = $CertificateThumbprint.Replace(' ', '')
$signatureLabel = 'Unsigned internal beta'
if ($thumbprint) {
    $signTool = Get-Command signtool.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
    if (-not $signTool) {
        $kitsRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
        if (Test-Path -LiteralPath $kitsRoot) {
            $signTool = Get-ChildItem -LiteralPath $kitsRoot -Filter signtool.exe -Recurse -File |
                Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
                Sort-Object FullName -Descending |
                Select-Object -First 1 -ExpandProperty FullName
        }
    }
    if (-not $signTool) { throw 'signtool.exe is required when a signing certificate is supplied' }
    & $signTool sign /sha1 $thumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 $launcher
    if ($LASTEXITCODE -ne 0) { throw "Launcher signing failed with exit code $LASTEXITCODE" }
    & $signTool verify /pa /all $launcher
    if ($LASTEXITCODE -ne 0) { throw "Launcher signature verification failed with exit code $LASTEXITCODE" }
    $signatureLabel = 'Authenticode signed'
} elseif ($RequireSignature) {
    throw 'A trusted code-signing certificate thumbprint is required for this release build'
} else {
    Write-Warning 'Research Starter.exe is unsigned. Supply -CertificateThumbprint or use -RequireSignature for publication builds.'
}
& robocopy (Join-Path $project 'runtime') (Join-Path $stage 'runtime') /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -gt 7) { throw "Runtime copy failed with robocopy exit code $LASTEXITCODE" }
& robocopy (Join-Path $project 'node_modules') (Join-Path $stage 'node_modules') /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -gt 7) { throw "Node dependency copy failed with robocopy exit code $LASTEXITCODE" }

$launcherHash = Get-Sha256WithRetry -LiteralPath $launcher
$noticePath = Join-Path $stage 'RELEASE-INTEGRITY.txt'
@"
Research Starter $Version
Release status: $signatureLabel

This internal beta may be unsigned. If Windows shows "Unknown publisher", verify that
the package came from the official GitHub Releases page and compare its SHA-256 values
with the checksums published beside the release. Do not use a copy from an unofficial source.

Research Starter.exe SHA256:
$launcherHash

Official releases:
https://github.com/DingRonghao/research-starter-sdk/releases
"@ | Set-Content -LiteralPath $noticePath -Encoding UTF8

Push-Location $dist
try {
    & tar.exe -a -cf "$name.zip" $name
    if ($LASTEXITCODE -ne 0) { throw "Release archive creation failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}

$hash = Get-Sha256WithRetry -LiteralPath $archive
$checksums = Join-Path $dist "$name-SHA256SUMS.txt"
@"
$hash  $name.zip
$launcherHash  $name/Research Starter.exe
"@ | Set-Content -LiteralPath $checksums -Encoding ASCII

$releaseBody = Join-Path $dist "$name-RELEASE.md"
@"
## Download verification

Release status: **$signatureLabel**.

This is an internal beta. Download it only from this repository's GitHub Releases page. If Windows reports an unknown publisher, verify the SHA-256 checksum before running it. The project does not ask users to install a self-signed root certificate.

``````text
$hash  $name.zip
$launcherHash  $name/Research Starter.exe
``````
"@ | Set-Content -LiteralPath $releaseBody -Encoding UTF8

Write-Output "Release: $archive"
Write-Output "SHA256: $hash"
Write-Output "Checksums: $checksums"
Write-Output "GitHub release text: $releaseBody"
