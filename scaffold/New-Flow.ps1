<#
.SYNOPSIS
    Stamp out a new flow from this template by filling in the per-flow values.

.DESCRIPTION
    Run this from the root of a freshly-created flow repo (created on GitHub via
    "Use this template", then cloned to C:\Prefect\<slug>). It rewrites the
    placeholder slug/repo/branch in prefect.yaml, flow.py and pyproject.toml.

.EXAMPLE
    .\scaffold\New-Flow.ps1 -Slug customer-sync `
        -RepoUrl https://github.com/our-org/customer-sync.git -Sync
#>
param(
    [Parameter(Mandatory = $true)][string]$Slug,
    [Parameter(Mandatory = $true)][string]$RepoUrl,
    [string]$Branch = "main",
    [switch]$Sync
)

$ErrorActionPreference = "Stop"

$files = @("prefect.yaml", "flow.py", "pyproject.toml")
foreach ($f in $files) {
    if (-not (Test-Path $f)) { continue }
    $text = Get-Content $f -Raw
    # Order matters: replace the full example URL (which contains the example
    # slug) BEFORE replacing the bare slug string. Use a literal replacement
    # (scriptblock) so characters like `$` in the URL aren't treated as regex.
    $text = [regex]::Replace($text, 'https://github\.com/our-org/nsf-example\.git', { $RepoUrl })
    $text = $text -replace 'nsf-example', $Slug
    $text = $text -replace 'origin/main', "origin/$Branch"
    $text = $text -replace '-b main', "-b $Branch"
    Set-Content -Path $f -Value $text -NoNewline
    Write-Host "Updated $f"
}

Write-Host ""
Write-Host "Flow '$Slug' scaffolded."
Write-Host "  repo   : $RepoUrl"
Write-Host "  branch : $Branch"
Write-Host "  folder : C:\Prefect\$Slug   (this repo should be checked out there)"

if ($Sync) {
    Write-Host "Running 'uv sync'..."
    uv sync
    Write-Host "uv sync complete."
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit flow.py with your logic; add deps to pyproject.toml then 'uv lock'."
Write-Host "  2. Review the schedule/tags in prefect.yaml (default deployment name is <slug>-scheduled)."
Write-Host "  3. Commit & push."
Write-Host "  4. 'prefect deploy' (with PREFECT_API_URL pointed at the server)."
