param(
    [Parameter(Mandatory = $true)]
    [string]$SpaceRepoUrl,
    [string]$OutputDir = "dist/huggingface-space",
    [string]$RepoDir = "dist/huggingface-space-repo",
    [string]$CommitMessage = "chore: publish PPE Sentinel Space",
    [switch]$Push
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

& (Join-Path $PSScriptRoot "export_hf_space.ps1") -OutputDir $OutputDir

$bundlePath = Join-Path $root $OutputDir
$repoPath = Join-Path $root $RepoDir

if (-not (Test-Path $repoPath)) {
    git clone $SpaceRepoUrl $repoPath | Out-Null
} elseif (-not (Test-Path (Join-Path $repoPath ".git"))) {
    throw "RepoDir exists but is not a git repository: $repoPath"
}

Push-Location $repoPath
git fetch origin main | Out-Null
git checkout main | Out-Null
git pull --ff-only origin main | Out-Null

Get-ChildItem -Force . | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force

foreach ($item in Get-ChildItem -Force $bundlePath) {
    Copy-Item -Recurse -Force $item.FullName .
}

git add .

$hasChanges = git status --short
if ($hasChanges) {
    git commit -m $CommitMessage
}

if ($Push) {
    git push -u origin main
} else {
    Write-Host "Space bundle is synced into $repoPath"
    Write-Host "Run 'git -C ""$repoPath"" push -u origin main' when you're ready to publish."
}

Pop-Location
