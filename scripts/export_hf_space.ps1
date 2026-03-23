param(
    [string]$OutputDir = "dist/huggingface-space"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$target = Join-Path $root $OutputDir

if (Test-Path $target) {
    Remove-Item -Recurse -Force $target
}

New-Item -ItemType Directory -Force -Path $target | Out-Null

$copyMap = @(
    @{ Source = "app"; Destination = "app" },
    @{ Source = "artifacts/.gitkeep"; Destination = "artifacts/.gitkeep" },
    @{ Source = "requirements.txt"; Destination = "requirements.txt" },
    @{ Source = "Dockerfile"; Destination = "Dockerfile" },
    @{ Source = ".dockerignore"; Destination = ".dockerignore" },
    @{ Source = ".env.example"; Destination = ".env.example" },
    @{ Source = "deploy/huggingface/README.md"; Destination = "README.md" }
)

foreach ($entry in $copyMap) {
    $source = Join-Path $root $entry.Source
    $destination = Join-Path $target $entry.Destination
    $destinationParent = Split-Path -Parent $destination
    if (-not (Test-Path $destinationParent)) {
        New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
    }
    Copy-Item -Recurse -Force $source $destination
}

Get-ChildItem -Path $target -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $target -Recurse -File -Include "*.pyc", "*.pyo" | Remove-Item -Force

Write-Host "Hugging Face Space bundle exported to $target"
