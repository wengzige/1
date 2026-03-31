param(
    [Parameter(Mandatory = $true)]
    [string]$ArticleDir,
    [switch]$AllowNativeLists
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

$scriptPath = Join-Path $workflowRoot 'scripts\publish-article.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Template publish script not found: $scriptPath"
}

& $scriptPath -ArticleDir $resolvedArticleDir -AllowNativeLists:$AllowNativeLists
