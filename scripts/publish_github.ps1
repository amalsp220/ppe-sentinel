param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,
    [string]$RemoteName = "origin",
    [string]$CommitMessage = "chore: bootstrap PPE Sentinel",
    [switch]$Push
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

git rev-parse --is-inside-work-tree | Out-Null

$remoteExists = git remote | Select-String -SimpleMatch $RemoteName
if (-not $remoteExists) {
    git remote add $RemoteName $RepoUrl
}

git add .

$hasChanges = git status --short
if ($hasChanges) {
    git commit -m $CommitMessage
}

if ($Push) {
    git push -u $RemoteName main
} else {
    Write-Host "Remote '$RemoteName' is configured."
    Write-Host "Run 'git push -u $RemoteName main' when you're ready to publish."
}
