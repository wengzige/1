param(
    [Parameter(Mandatory = $true)]
    [string]$Title,
    [string]$Author = '',
    [string]$SourceUrl = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $projectRoot
$templateRoot = Join-Path $projectRoot 'templates'
$articleHome = Join-Path $repoRoot 'output'

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Convert-ToSafeFolderName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $invalidChars = [System.IO.Path]::GetInvalidFileNameChars()
    $builder = New-Object System.Text.StringBuilder

    foreach ($ch in $Value.ToCharArray()) {
        if ($invalidChars -contains $ch) {
            [void]$builder.Append('-')
        }
        else {
            [void]$builder.Append($ch)
        }
    }

    $name = $builder.ToString().Trim().TrimEnd('.')
    if ([string]::IsNullOrWhiteSpace($name)) {
        throw 'The title becomes an empty folder name after sanitization.'
    }

    return $name
}

function Render-Template {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TemplatePath,
        [Parameter(Mandatory = $true)]
        [hashtable]$Tokens
    )

    $content = Get-Content -LiteralPath $TemplatePath -Raw -Encoding UTF8
    foreach ($key in $Tokens.Keys) {
        $content = $content.Replace($key, $Tokens[$key])
    }

    return $content
}

$folderName = Convert-ToSafeFolderName -Value $Title
$articleDir = Join-Path $articleHome $folderName

if ((Test-Path -LiteralPath $articleDir) -and -not $Force) {
    throw "Article folder already exists: $articleDir"
}

New-Item -ItemType Directory -Force -Path $articleHome | Out-Null
New-Item -ItemType Directory -Force -Path $articleDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $articleDir 'assets') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $articleDir 'generated') | Out-Null

$tokens = @{
    '__TITLE__' = $Title
    '__AUTHOR__' = $Author
    '__SOURCE_URL__' = $SourceUrl
}

$files = @(
    @{
        Template = (Join-Path $templateRoot 'article.md.template')
        Output = (Join-Path $articleDir 'article.md')
    },
    @{
        Template = (Join-Path $templateRoot 'draft-metadata.json.template')
        Output = (Join-Path $articleDir 'draft-metadata.json')
    },
    @{
        Template = (Join-Path $templateRoot 'article-body.template.html.template')
        Output = (Join-Path $articleDir 'article-body.template.html')
    },
    @{
        Template = (Join-Path $templateRoot 'image-prompts.md.template')
        Output = (Join-Path $articleDir 'generated\image-prompts.md')
    }
)

foreach ($file in $files) {
    $rendered = Render-Template -TemplatePath $file.Template -Tokens $tokens
    Write-Utf8NoBom -Path $file.Output -Content $rendered
}

[pscustomobject]@{
    article_dir = $articleDir
    folder_name = $folderName
    article_file = (Join-Path $articleDir 'article.md')
    html_template = (Join-Path $articleDir 'article-body.template.html')
    metadata_file = (Join-Path $articleDir 'draft-metadata.json')
    image_prompt_file = (Join-Path $articleDir 'generated\image-prompts.md')
} | ConvertTo-Json -Depth 5
