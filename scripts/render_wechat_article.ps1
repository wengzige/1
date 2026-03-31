param(
    [Parameter(Mandatory = $true)]
    [string]$ArticleDir,
    [string]$Theme = ''
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$workflowRoot = Join-Path $repoRoot 'skill2 paibanyouhua'

function Resolve-ManagedArticleDir {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        if (-not (Test-Path -LiteralPath $PathValue)) {
            throw "Article folder not found: $PathValue"
        }
        return (Resolve-Path -LiteralPath $PathValue).Path
    }

    $candidates = @(
        (Join-Path $repoRoot $PathValue),
        (Join-Path (Join-Path $repoRoot 'output') $PathValue)
    ) | Select-Object -Unique

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Article folder not found. Tried: $($candidates -join ', ')"
}

$resolvedArticleDir = Resolve-ManagedArticleDir -PathValue $ArticleDir

if (-not (Test-Path -LiteralPath $resolvedArticleDir)) {
    throw "Article folder not found: $resolvedArticleDir"
}

$scriptPath = Join-Path $workflowRoot 'scripts\render-article.py'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Template render script not found: $scriptPath"
}

$args = @($scriptPath, '--article-dir', $resolvedArticleDir)
if (-not [string]::IsNullOrWhiteSpace($Theme)) {
    $args += @('--theme', $Theme)
}

& python @args
if ($LASTEXITCODE -ne 0) {
    throw "Template render step failed for: $resolvedArticleDir"
}

$qualityScriptPath = Join-Path $workflowRoot 'scripts\run-quality-gates.py'
if (-not (Test-Path -LiteralPath $qualityScriptPath)) {
    throw "Quality gate script not found: $qualityScriptPath"
}

& python $qualityScriptPath --article-dir $resolvedArticleDir
if ($LASTEXITCODE -ne 0) {
    throw "Quality gate step failed for: $resolvedArticleDir"
}
