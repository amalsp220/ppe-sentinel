param(
    [Parameter(Mandatory = $true)]
    [string]$SpaceRepoUrl,
    [string]$OutputDir = "dist/huggingface-space",
    [string]$CommitMessage = "chore: publish PPE Sentinel Space",
    [switch]$Push
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

& (Join-Path $PSScriptRoot "export_hf_space.ps1") -OutputDir $OutputDir

$spacePath = Join-Path $root $OutputDir
Push-Location $spacePath

if (-not (Test-Path ".git")) {
    git init -b main | Out-Null
}

$remoteExists = git remote | Select-String -SimpleMatch "origin"
if (-not $remoteExists) {
    git remote add origin $SpaceRepoUrl
}

git add .

$hasChanges = git status --short
if ($hasChanges) {
    git commit -m $CommitMessage
}

if ($Push) {
    git push -u origin main
} else {
    Write-Host "Space bundle is ready at $spacePath"
    Write-Host "Run 'git -C ""$spacePath"" push -u origin main' when you're ready to publish."
}

Pop-Location
