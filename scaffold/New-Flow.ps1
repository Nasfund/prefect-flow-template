<#
.SYNOPSIS
    Stamp out a new flow from this template: fill in the per-flow values and create
    a blank spec for it.

.DESCRIPTION
    Run this from the root of a freshly-created flow repo (created on GitHub via
    "Use this template", then cloned to C:\Prefect\<slug>). It:

      1. rewrites the placeholder slug/repo/branch in prefect.yaml, flow.py and
         pyproject.toml;
      2. creates .kiro/specs/<slug>/ from scaffold/spec-templates/ — the spec you
         fill in with Kiro before writing any flow code;
      3. removes the shipped nsf-example reference spec (keep it with
         -KeepExampleSpec);
      4. with -Sync, runs `uv sync` and then `uv run pytest` so the fresh repo
         proves itself immediately.

    The test suite reads the slug from pyproject.toml, so nothing under tests/ needs
    rewriting — it adapts to whatever slug you scaffold with.

.PARAMETER Slug
    Lowercase kebab-case flow identity. Must equal the GitHub repo name and the
    C:\Prefect\<slug> checkout folder.

.PARAMETER KeepExampleSpec
    Keep .kiro/specs/nsf-example/ as a worked reference instead of deleting it.

.PARAMETER Sync
    Run `uv sync` and `uv run pytest` after scaffolding.

.EXAMPLE
    .\scaffold\New-Flow.ps1 -Slug customer-sync `
        -RepoUrl https://github.com/our-org/customer-sync.git -Sync
#>
param(
    [Parameter(Mandatory = $true)][string]$Slug,
    [Parameter(Mandatory = $true)][string]$RepoUrl,
    [string]$Branch = "main",
    [switch]$Sync,
    [switch]$KeepExampleSpec
)

$ErrorActionPreference = "Stop"

$ExampleSlug = "nsf-example"

# The slug lands in a Windows path, a GitHub repo name, a Prefect flow name and a
# deployment name. Catch a bad one here rather than after it has been written into
# five files. (tests/test_deployment_config.py enforces the same shape.)
# -cnotmatch, not -notmatch: PowerShell's -match is case-INsensitive by default, so
# a plain [a-z0-9] pattern would happily accept 'Customer-Sync'.
if ($Slug -cnotmatch '^[a-z0-9]+(-[a-z0-9]+)*$') {
    throw "Slug '$Slug' must be lowercase kebab-case, e.g. 'nsf-idos-refresh'."
}

if (-not (Test-Path "prefect.yaml")) {
    throw "Run this from the repo root (no prefect.yaml found in '$PWD')."
}

# ---------------------------------------------------------------------------------
# 1. Per-flow placeholders
# ---------------------------------------------------------------------------------

$files = @("prefect.yaml", "flow.py", "pyproject.toml")
foreach ($f in $files) {
    if (-not (Test-Path $f)) { continue }
    $text = Get-Content $f -Raw
    # Order matters: replace the full example URL (which contains the example
    # slug) BEFORE replacing the bare slug string. Use a literal replacement
    # (scriptblock) so characters like `$` in the URL aren't treated as regex.
    $text = [regex]::Replace($text, 'https://github\.com/our-org/nsf-example\.git', { $RepoUrl })
    $text = [regex]::Replace($text, [regex]::Escape($ExampleSlug), { $Slug })
    $text = $text -replace 'origin/main', "origin/$Branch"
    $text = $text -replace '-b main', "-b $Branch"
    Set-Content -Path $f -Value $text -NoNewline
    Write-Host "Updated $f"
}

# ---------------------------------------------------------------------------------
# 2. Spec skeleton for this flow
# ---------------------------------------------------------------------------------

$templateDir = Join-Path "scaffold" "spec-templates"
$specDir = Join-Path ".kiro" (Join-Path "specs" $Slug)

if (-not (Test-Path $templateDir)) {
    Write-Warning "No $templateDir found - skipping spec creation."
}
elseif (Test-Path $specDir) {
    Write-Warning "$specDir already exists - leaving it untouched."
}
else {
    New-Item -ItemType Directory -Path $specDir -Force | Out-Null
    foreach ($template in Get-ChildItem -Path $templateDir -Filter "*.md") {
        $body = Get-Content $template.FullName -Raw
        $body = [regex]::Replace($body, '<slug>', { $Slug })
        Set-Content -Path (Join-Path $specDir $template.Name) -Value $body -NoNewline
    }
    Write-Host "Created $specDir (requirements.md, design.md, tasks.md)"
}

# ---------------------------------------------------------------------------------
# 3. The shipped reference spec
# ---------------------------------------------------------------------------------

$exampleSpecDir = Join-Path ".kiro" (Join-Path "specs" $ExampleSlug)
if (Test-Path $exampleSpecDir) {
    if ($KeepExampleSpec) {
        Write-Host "Keeping the reference spec at $exampleSpecDir (-KeepExampleSpec)."
    }
    elseif ($Slug -eq $ExampleSlug) {
        Write-Host "Slug is '$ExampleSlug' - keeping the existing spec."
    }
    else {
        Remove-Item -Recurse -Force $exampleSpecDir
        Write-Host "Removed the reference spec at $exampleSpecDir"
    }
}

# ---------------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------------

Write-Host ""
Write-Host "Flow '$Slug' scaffolded."
Write-Host "  repo   : $RepoUrl"
Write-Host "  branch : $Branch"
Write-Host "  folder : C:\Prefect\$Slug   (this repo should be checked out there)"
Write-Host "  spec   : $specDir"

$testsFailed = $false
if ($Sync) {
    Write-Host ""
    Write-Host "Running 'uv sync'..."
    uv sync
    if ($LASTEXITCODE -ne 0) { throw "uv sync failed." }

    Write-Host "Running 'uv run pytest'..."
    uv run pytest
    if ($LASTEXITCODE -ne 0) {
        $testsFailed = $true
        Write-Warning "Tests failed. Fix these before writing any flow code - a red suite here usually means the slug was only partially applied."
    }
    else {
        Write-Host "Tests pass - the scaffolded repo is consistent."
    }
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Describe your flow to Kiro and fill in $specDir\requirements.md,"
Write-Host "     then design.md and tasks.md. Spec first - don't start with flow.py."
Write-Host "  2. Work through tasks.md: write the test, then the code in flow.py."
Write-Host "     Add dependencies to pyproject.toml, run 'uv lock', commit uv.lock."
Write-Host "  3. Review the schedule/tags in prefect.yaml (deployment defaults to '$Slug-scheduled')."
Write-Host "  4. Gate: 'uv run pytest' must be green."
Write-Host "  5. Commit & push - only pushed code ever runs in production."
Write-Host "  6. 'prefect deploy' (with PREFECT_API_URL pointed at the server), then"
Write-Host "     trigger a run and confirm the logs show"
Write-Host "     C:\Prefect\$Slug\.venv\Scripts\python.exe"

if ($testsFailed) { exit 1 }
