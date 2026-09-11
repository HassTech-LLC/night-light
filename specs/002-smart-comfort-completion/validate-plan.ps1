# Read-only structural checks for this planning package, not product tests.
$ErrorActionPreference = 'Stop'
$planDirectory = $PSScriptRoot
$planFiles = @(Get-ChildItem -LiteralPath $planDirectory -Filter '*.md' -File -Recurse)
$planErrors = [System.Collections.Generic.List[string]]::new()
$planLinkCount = 0
foreach ($planFile in $planFiles) {
    $planContent = [System.IO.File]::ReadAllText($planFile.FullName)
    foreach ($planLink in [regex]::Matches($planContent, '\[[^\]]+\]\(([^)]+)\)')) {
        $planTarget = $planLink.Groups[1].Value.Trim('<','>')
        if ($planTarget -match '^(https?://|#|mailto:)') { continue }
        $planTarget = ($planTarget -split '#')[0]
        $planResolved = [System.IO.Path]::GetFullPath((Join-Path $planFile.DirectoryName $planTarget))
        $planLinkCount++
        if (-not (Test-Path -LiteralPath $planResolved)) { $planErrors.Add("Broken link: $($planFile.Name) -> $planTarget") }
    }
    if ($planContent -match '(?m)[ \t]+$') { $planErrors.Add("Trailing whitespace: $($planFile.Name)") }
    if ($planContent -match 'NEEDS CLARIFICATION|\[FEATURE\]|TXXX') { $planErrors.Add("Unfilled template: $($planFile.Name)") }
}
$planTaskContent = [System.IO.File]::ReadAllText((Join-Path $planDirectory 'tasks.md'))
$planTasks = @([regex]::Matches($planTaskContent, '(?m)^- \[ \] (T\d{3}) (.*)$'))
if ($planTasks.Count -ne 68) { $planErrors.Add("Expected 68 tasks, found $($planTasks.Count)") }
for ($planIndex = 0; $planIndex -lt $planTasks.Count; $planIndex++) {
    $planExpected = 'T{0:D3}' -f ($planIndex + 1)
    if ($planTasks[$planIndex].Groups[1].Value -ne $planExpected) { $planErrors.Add("Nonsequential task at $planExpected") }
    if ($planTasks[$planIndex].Groups[2].Value -notmatch '\S+/\S*|\S+\.(py|md|json|cs|html|css|js|astro|ts|nsi|yml)\b') { $planErrors.Add("Missing file path: $planExpected") }
}
if ($planTaskContent -match '(?m)^- \[[xX]\]') { $planErrors.Add('Implementation tasks must remain unchecked at planning handoff') }
$planSpec = [System.IO.File]::ReadAllText((Join-Path $planDirectory 'spec.md'))
$planFr = @([regex]::Matches($planSpec, '\bFR-\d{3}\b') | ForEach-Object Value | Sort-Object -Unique)
$planNfr = @([regex]::Matches($planSpec, '\bNFR-\d{3}\b') | ForEach-Object Value | Sort-Object -Unique)
if ($planFr.Count -ne 20 -or $planNfr.Count -ne 6) { $planErrors.Add('Requirement inventory mismatch') }
$planStoryCounts = [ordered]@{}
foreach ($planStory in 1..6) {
    $planStoryCounts["US$planStory"] = @($planTasks | Where-Object { $_.Groups[2].Value -match "\[US$planStory\]" }).Count
}
[ordered]@{
    kind = 'planning_structure_only'
    markdown_files = $planFiles.Count
    local_links_checked = $planLinkCount
    tasks = $planTasks.Count
    functional_requirements = $planFr.Count
    nonfunctional_requirements = $planNfr.Count
    story_task_counts = $planStoryCounts
    errors = @($planErrors)
    result = $(if ($planErrors.Count) { 'failed' } else { 'passed' })
} | ConvertTo-Json -Depth 4
if ($planErrors.Count) { exit 1 }
