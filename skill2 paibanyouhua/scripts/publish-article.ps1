param(
    [Parameter(Mandatory = $true)]
    [string]$ArticleDir,
    [switch]$AllowNativeLists
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $projectRoot '.local\bin\md2wechat.exe'

$env:HOME = $projectRoot
$env:USERPROFILE = $projectRoot
$env:PATH = "$projectRoot\.local\bin;$env:PATH"

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

function Get-JsonOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $exe @($Args + '--json') 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $raw = (($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine).Trim()
    $successIndex = $raw.IndexOf('"success"')

    if ($successIndex -lt 0) {
        throw "md2wechat did not return a success JSON object. ExitCode=$exitCode Raw output:`n$raw"
    }

    $start = -1
    for ($i = $successIndex; $i -ge 0; $i--) {
        if ($raw[$i] -eq '{') {
            $start = $i
            break
        }
    }

    if ($start -lt 0) {
        throw "Could not locate the start of the JSON object. Raw output:`n$raw"
    }

    $depth = 0
    $inString = $false
    $escaped = $false
    $end = -1

    for ($i = $start; $i -lt $raw.Length; $i++) {
        $ch = $raw[$i]

        if ($escaped) {
            $escaped = $false
            continue
        }

        if ($ch -eq '\') {
            if ($inString) {
                $escaped = $true
            }
            continue
        }

        if ($ch -eq '"') {
            $inString = -not $inString
            continue
        }

        if (-not $inString) {
            if ($ch -eq '{') {
                $depth++
            }
            elseif ($ch -eq '}') {
                $depth--
                if ($depth -eq 0) {
                    $end = $i
                    break
                }
            }
        }
    }

    if ($end -lt $start) {
        throw "Could not locate the end of the JSON object. Raw output:`n$raw"
    }

    $json = $raw.Substring($start, $end - $start + 1)
    $obj = $json | ConvertFrom-Json

    if (-not $obj.success) {
        $reason = if ($obj.error) { $obj.error } else { $obj.message }
        throw $reason
    }

    return $obj
}

function Get-FieldValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Object,
        [Parameter(Mandatory = $true)]
        [string]$Primary,
        [Parameter(Mandatory = $false)]
        [string]$Nested
    )

    if ($Object.PSObject.Properties.Name -contains $Primary) {
        return $Object.$Primary
    }

    if ($Nested -and $Object.PSObject.Properties.Name -contains 'data') {
        $data = $Object.data
        if ($data -and $data.PSObject.Properties.Name -contains $Nested) {
            return $data.$Nested
        }
    }

    return $null
}

function Resolve-ArticleFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseDir,
        [string]$RelativePath,
        [string[]]$Fallbacks = @()
    )

    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($RelativePath)) {
        $candidates += $RelativePath
    }
    $candidates += $Fallbacks

    foreach ($candidate in $candidates) {
        $normalized = $candidate.Replace('/', '\')
        $fullPath = Join-Path $BaseDir $normalized
        if (Test-Path -LiteralPath $fullPath) {
            return (Resolve-Path -LiteralPath $fullPath).Path
        }
    }

    $tried = $candidates -join ', '
    throw "Required file not found in article folder. Tried: $tried"
}

function Upload-ImageAndGetUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $upload = Get-JsonOutput -Args @('upload_image', $Path)
    $wechatUrl = Get-FieldValue -Object $upload -Primary 'wechat_url' -Nested 'wechat_url'

    if (-not $wechatUrl) {
        throw "Image upload succeeded but wechat_url was not found for $Path"
    }

    return @{
        url = $wechatUrl
        media_id = (Get-FieldValue -Object $upload -Primary 'media_id' -Nested 'media_id')
    }
}

function New-PreflightReport {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArticleRoot,
        [Parameter(Mandatory = $true)]
        [bool]$AllowNativeLists
    )

    return [ordered]@{
        article_dir = $ArticleRoot
        allow_native_lists = $AllowNativeLists
        errors = New-Object System.Collections.Generic.List[string]
        warnings = New-Object System.Collections.Generic.List[string]
    }
}

function Add-ReportItem {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Report,
        [Parameter(Mandatory = $true)]
        [ValidateSet('errors', 'warnings')]
        [string]$Level,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $Report[$Level].Add($Message)
}

function Test-SuspiciousQuestionRuns {
    param(
        [AllowEmptyString()]
        [string]$Text
    )

    if ([string]::IsNullOrEmpty($Text)) {
        return $false
    }

    return [regex]::IsMatch($Text, '\?{3,}')
}

function Test-SuspiciousMojibakeText {
    param(
        [AllowEmptyString()]
        [string]$Text
    )

    if ([string]::IsNullOrEmpty($Text)) {
        return $false
    }

    $consecutive = 0
    $total = 0
    foreach ($char in $Text.ToCharArray()) {
        $codepoint = [int][char]$char
        if ($codepoint -ge 0x0080 -and $codepoint -le 0x00FF) {
            $consecutive++
            $total++
            if ($consecutive -ge 3 -or $total -ge 6) {
                return $true
            }
        }
        else {
            $consecutive = 0
        }
    }

    return $false
}

if (-not (Test-Path -LiteralPath $ArticleDir)) {
    throw "Article folder not found: $ArticleDir"
}

$articleRoot = (Resolve-Path -LiteralPath $ArticleDir).Path
$renderScriptPath = Join-Path $PSScriptRoot 'render-article.py'
if (-not (Test-Path -LiteralPath $renderScriptPath)) {
    throw "Template render script not found: $renderScriptPath"
}

$renderOutput = & python $renderScriptPath --article-dir $articleRoot 2>&1
if ($LASTEXITCODE -ne 0) {
    $rawRender = (($renderOutput | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine).Trim()
    throw "Template render step failed:`n$rawRender"
}

$qualityScriptPath = Join-Path $PSScriptRoot 'run-quality-gates.py'
if (-not (Test-Path -LiteralPath $qualityScriptPath)) {
    throw "Quality gate script not found: $qualityScriptPath"
}

$qualityOutput = & python $qualityScriptPath --article-dir $articleRoot --strict 2>&1
if ($LASTEXITCODE -ne 0) {
    $rawQuality = (($qualityOutput | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine).Trim()
    throw "Quality gate step failed:`n$rawQuality"
}

$metaPath = Join-Path $articleRoot 'draft-metadata.json'
$articlePath = Join-Path $articleRoot 'article.md'
$htmlTemplatePath = Join-Path $articleRoot 'article-body.template.html'
$generatedDir = Join-Path $articleRoot 'generated'
$humannessReportPath = Join-Path $generatedDir 'humanness-report.json'
$qualityGatesPath = Join-Path $generatedDir 'quality-gates.json'
$outputHtmlPath = Join-Path $generatedDir 'output.html'
$draftJsonPath = Join-Path $generatedDir 'draft.json'
$resultPath = Join-Path $generatedDir 'publish-result.json'
$preflightPath = Join-Path $generatedDir 'preflight-report.json'
$imagePromptPath = Join-Path $generatedDir 'image-prompts.md'

New-Item -ItemType Directory -Force -Path $generatedDir | Out-Null

$report = New-PreflightReport -ArticleRoot $articleRoot -AllowNativeLists ([bool]$AllowNativeLists)
$report['humanness_report_path'] = $humannessReportPath
$report['quality_gates_path'] = $qualityGatesPath
$report['humanness_summary'] = $null

if (-not (Test-Path -LiteralPath $exe)) {
    Add-ReportItem -Report $report -Level errors -Message "md2wechat executable not found: $exe"
}
if (-not (Test-Path -LiteralPath $metaPath)) {
    Add-ReportItem -Report $report -Level errors -Message "Missing metadata file: $metaPath"
}
if (-not (Test-Path -LiteralPath $htmlTemplatePath)) {
    Add-ReportItem -Report $report -Level errors -Message "Missing HTML template file: $htmlTemplatePath"
}

$metadata = $null
$markdown = ''
$html = ''
$humannessReport = $null

if ($report.errors.Count -eq 0) {
    try {
        $metadata = Get-Content -LiteralPath $metaPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        Add-ReportItem -Report $report -Level errors -Message "draft-metadata.json is not valid UTF-8 JSON: $($_.Exception.Message)"
    }

    try {
        $html = Get-Content -LiteralPath $htmlTemplatePath -Raw -Encoding UTF8
    }
    catch {
        Add-ReportItem -Report $report -Level errors -Message "article-body.template.html could not be read as UTF-8: $($_.Exception.Message)"
    }

    if (Test-Path -LiteralPath $articlePath) {
        try {
            $markdown = Get-Content -LiteralPath $articlePath -Raw -Encoding UTF8
        }
        catch {
            Add-ReportItem -Report $report -Level errors -Message "article.md could not be read as UTF-8: $($_.Exception.Message)"
        }
    }

    if (-not (Test-Path -LiteralPath $humannessReportPath)) {
        Add-ReportItem -Report $report -Level errors -Message "Missing humanness report: $humannessReportPath"
    }
    else {
        try {
            $humannessReport = Get-Content -LiteralPath $humannessReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
        }
        catch {
            Add-ReportItem -Report $report -Level errors -Message "humanness-report.json is not valid UTF-8 JSON: $($_.Exception.Message)"
        }
    }

    if (-not (Test-Path -LiteralPath $qualityGatesPath)) {
        Add-ReportItem -Report $report -Level errors -Message "Missing quality gate report: $qualityGatesPath"
    }
}

if ($metadata) {
    if ([string]::IsNullOrWhiteSpace([string]$metadata.title)) {
        Add-ReportItem -Report $report -Level errors -Message 'Metadata title is empty.'
    }
    if ([string]::IsNullOrWhiteSpace([string]$metadata.cover_image)) {
        Add-ReportItem -Report $report -Level warnings -Message 'Metadata cover_image is empty. The script will fall back to assets/cover-wide.jpg if present.'
    }
    if (Test-SuspiciousQuestionRuns -Text ([string]$metadata.title)) {
        Add-ReportItem -Report $report -Level errors -Message 'Suspicious question-mark runs detected in metadata title. This usually means garbled text.'
    }
    if (Test-SuspiciousMojibakeText -Text ([string]$metadata.title)) {
        Add-ReportItem -Report $report -Level errors -Message 'Suspicious mojibake text detected in metadata title. This usually means broken encoding.'
    }
    if (Test-SuspiciousQuestionRuns -Text ([string]$metadata.digest)) {
        Add-ReportItem -Report $report -Level errors -Message 'Suspicious question-mark runs detected in metadata digest. This usually means garbled text.'
    }
    if (Test-SuspiciousMojibakeText -Text ([string]$metadata.digest)) {
        Add-ReportItem -Report $report -Level errors -Message 'Suspicious mojibake text detected in metadata digest. This usually means broken encoding.'
    }
}

if ($html) {
    if ($html -match '<!--') {
        Add-ReportItem -Report $report -Level errors -Message 'HTML comments detected in article-body.template.html. Remove editor notes before publishing.'
    }

    if (Test-SuspiciousQuestionRuns -Text $html) {
        Add-ReportItem -Report $report -Level errors -Message 'Suspicious question-mark runs detected in article-body.template.html. This usually means garbled text.'
    }
    if (Test-SuspiciousMojibakeText -Text $html) {
        Add-ReportItem -Report $report -Level errors -Message 'Suspicious mojibake text detected in article-body.template.html. This usually means broken encoding.'
    }

    if ($html.Contains('{{TITLE}}') -or $html.Contains('{{AUTHOR}}') -or $html.Contains('{{DIGEST}}') -or $html.Contains('{{SOURCE_URL}}')) {
        Add-ReportItem -Report $report -Level errors -Message 'Unrendered template placeholders detected in article-body.template.html.'
    }

    if ($html.Contains([char]0xFFFD)) {
        Add-ReportItem -Report $report -Level errors -Message 'Replacement character � detected in article-body.template.html. Check file encoding before publishing.'
    }

    if ([regex]::IsMatch($html, '<\s*(ul|ol|li)\b', 'IgnoreCase')) {
        if ($AllowNativeLists) {
            Add-ReportItem -Report $report -Level warnings -Message 'Native list tags detected in article-body.template.html. Publishing continues only because -AllowNativeLists was provided.'
        }
        else {
            Add-ReportItem -Report $report -Level errors -Message 'Native list tags detected in article-body.template.html. Replace them with paragraphs or card-style div blocks, or publish with -AllowNativeLists only after preview verification.'
        }
    }

    if ($html -match '\{\{BODY_IMAGE_URL\}\}') {
        Add-ReportItem -Report $report -Level warnings -Message 'Legacy {{BODY_IMAGE_URL}} placeholder detected. Prefer {{IMAGE:assets/body-visual.png}}.'
    }

    $placeholderMatches = [regex]::Matches($html, '\{\{([^}]+)\}\}')
    foreach ($match in $placeholderMatches) {
        $token = $match.Groups[1].Value.Trim()
        if ($token -notin @('TITLE', 'AUTHOR', 'DIGEST', 'SOURCE_URL', 'BODY_IMAGE_URL') -and $token -notmatch '^IMAGE:.+') {
            Add-ReportItem -Report $report -Level errors -Message "Unknown placeholder detected: {{$token}}"
        }
    }
}

if ($markdown -and (Test-SuspiciousQuestionRuns -Text $markdown)) {
    Add-ReportItem -Report $report -Level errors -Message 'Suspicious question-mark runs detected in article.md. This usually means garbled text.'
}
if ($markdown -and (Test-SuspiciousMojibakeText -Text $markdown)) {
    Add-ReportItem -Report $report -Level errors -Message 'Suspicious mojibake text detected in article.md. This usually means broken encoding.'
}

if (-not (Test-Path -LiteralPath $imagePromptPath)) {
    Add-ReportItem -Report $report -Level warnings -Message 'generated/image-prompts.md is missing. If this article involves direct image generation, add the prompts before delivery.'
}

if ($humannessReport) {
    $failedChecks = @()
    if ($humannessReport.summary -and $humannessReport.summary.failed_checks) {
        $failedChecks = @($humannessReport.summary.failed_checks)
    }

    $report['humanness_summary'] = [ordered]@{
        composite_score = $humannessReport.composite_score
        layer1_passed = if ($humannessReport.summary) { $humannessReport.summary.layer1_passed } else { $null }
        layer1_total = if ($humannessReport.summary) { $humannessReport.summary.layer1_total } else { $null }
        failed_checks = $failedChecks
        layer2_is_stub = if ($humannessReport.summary) { [bool]$humannessReport.summary.layer2_is_stub } else { $null }
    }

    if ($humannessReport.summary -and [bool]$humannessReport.summary.layer2_is_stub) {
        Add-ReportItem -Report $report -Level warnings -Message 'Humanness report used the stub LLM judge. Layer 1 checklist is valid; subjective judge is not yet fully wired.'
    }

    if ($failedChecks.Count -gt 0) {
        Add-ReportItem -Report $report -Level warnings -Message "Humanness checklist has failed items: $($failedChecks -join ', ')"
    }
}

$reportJson = $report | ConvertTo-Json -Depth 10
Write-Utf8NoBom -Path $preflightPath -Content $reportJson

if ($report.errors.Count -gt 0) {
    $message = @($report.errors | ForEach-Object { "- $_" }) -join [Environment]::NewLine
    throw "Preflight failed:`n$message"
}

$coverPath = Resolve-ArticleFile -BaseDir $articleRoot -RelativePath $metadata.cover_image -Fallbacks @('assets/cover-wide.jpg', 'cover-wide.jpg')
$coverUpload = Upload-ImageAndGetUrl -Path $coverPath
$coverMediaId = $coverUpload.media_id

if (-not $coverMediaId) {
    throw 'Cover upload succeeded but media_id was not found in the JSON response.'
}

$html = $html.Replace('{{TITLE}}', [string]$metadata.title)
$html = $html.Replace('{{AUTHOR}}', [string]$metadata.author)
$html = $html.Replace('{{DIGEST}}', [string]$metadata.digest)
$html = $html.Replace('{{SOURCE_URL}}', [string]$metadata.content_source_url)

if ($html.Contains('{{BODY_IMAGE_URL}}')) {
    $legacyBodyImagePath = Resolve-ArticleFile -BaseDir $articleRoot -RelativePath $null -Fallbacks @('assets/body-visual.png', 'body-visual.png')
    $legacyBodyUpload = Upload-ImageAndGetUrl -Path $legacyBodyImagePath
    $html = $html.Replace('{{BODY_IMAGE_URL}}', $legacyBodyUpload.url)
}

$imageUrlCache = @{}
$pattern = '\{\{IMAGE:([^}]+)\}\}'
$html = [regex]::Replace(
    $html,
    $pattern,
    {
        param($match)

        $relativeImagePath = $match.Groups[1].Value.Trim()
        if (-not $imageUrlCache.ContainsKey($relativeImagePath)) {
            $resolvedImagePath = Resolve-ArticleFile -BaseDir $articleRoot -RelativePath $relativeImagePath
            $imageUpload = Upload-ImageAndGetUrl -Path $resolvedImagePath
            $imageUrlCache[$relativeImagePath] = $imageUpload.url
        }

        return $imageUrlCache[$relativeImagePath]
    }
)

$renderedPayload = @([string]$metadata.title, [string]$metadata.digest, $html) -join [Environment]::NewLine
if (Test-SuspiciousQuestionRuns -Text $renderedPayload) {
    throw 'Suspicious question-mark runs detected in rendered draft payload. Fix garbled text before publishing.'
}
if (Test-SuspiciousMojibakeText -Text $renderedPayload) {
    throw 'Suspicious mojibake text detected in rendered draft payload. Fix broken encoding before publishing.'
}

$remainingPlaceholders = [regex]::Matches($html, '\{\{[^}]+\}\}')
if ($remainingPlaceholders.Count -gt 0) {
    $remaining = $remainingPlaceholders | ForEach-Object { $_.Value } | Select-Object -Unique
    throw "Unresolved placeholders remain after rendering: $($remaining -join ', ')"
}

Write-Utf8NoBom -Path $outputHtmlPath -Content $html

$needOpenComment = 1
if ($metadata.PSObject.Properties.Name -contains 'need_open_comment' -and $null -ne $metadata.need_open_comment) {
    $needOpenComment = [int]$metadata.need_open_comment
}

$onlyFansCanComment = 0
if ($metadata.PSObject.Properties.Name -contains 'only_fans_can_comment' -and $null -ne $metadata.only_fans_can_comment) {
    $onlyFansCanComment = [int]$metadata.only_fans_can_comment
}

$draft = @{
    articles = @(
        @{
            article_type = 'news'
            title = $metadata.title
            author = $metadata.author
            digest = $metadata.digest
            content = $html
            content_source_url = $metadata.content_source_url
            thumb_media_id = $coverMediaId
            need_open_comment = $needOpenComment
            only_fans_can_comment = $onlyFansCanComment
        }
    )
}

$draftJson = $draft | ConvertTo-Json -Depth 20
Write-Utf8NoBom -Path $draftJsonPath -Content $draftJson
$publishResult = Get-JsonOutput -Args @('create_draft', $draftJsonPath)
$resultJson = $publishResult | ConvertTo-Json -Depth 20
Write-Utf8NoBom -Path $resultPath -Content $resultJson
$publishResult | ConvertTo-Json -Depth 20
