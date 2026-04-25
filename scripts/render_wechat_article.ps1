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

$env:WEWRITE_RENDER_SCRIPT = $scriptPath
$env:WEWRITE_RENDER_ARTICLE_DIR = $resolvedArticleDir
$env:WEWRITE_RENDER_THEME = $Theme
$renderRunner = @'
import importlib.util
import os
import sys

script = os.environ["WEWRITE_RENDER_SCRIPT"]
article_dir = os.environ["WEWRITE_RENDER_ARTICLE_DIR"]
theme = os.environ.get("WEWRITE_RENDER_THEME", "").strip()
spec = importlib.util.spec_from_file_location("render_article", script)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.argv = [script, "--article-dir", article_dir]
if theme:
    sys.argv += ["--theme", theme]
raise SystemExit(module.main())
'@

$renderRunner | python -
if ($LASTEXITCODE -ne 0) {
    throw "Template render step failed for: $resolvedArticleDir"
}

$qualityScriptPath = Join-Path $workflowRoot 'scripts\run-quality-gates.py'
if (-not (Test-Path -LiteralPath $qualityScriptPath)) {
    throw "Quality gate script not found: $qualityScriptPath"
}

$env:WEWRITE_QUALITY_SCRIPT = $qualityScriptPath
$env:WEWRITE_QUALITY_ARTICLE_DIR = $resolvedArticleDir
$qualityRunner = @'
import importlib.util
import os
import sys

script = os.environ["WEWRITE_QUALITY_SCRIPT"]
article_dir = os.environ["WEWRITE_QUALITY_ARTICLE_DIR"]
spec = importlib.util.spec_from_file_location("run_quality_gates", script)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.argv = [script, "--article-dir", article_dir, "--strict"]
raise SystemExit(module.main())
'@

$qualityRunner | python -
if ($LASTEXITCODE -ne 0) {
    throw "Quality gate step failed for: $resolvedArticleDir"
}
