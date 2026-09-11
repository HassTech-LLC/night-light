param(
    [Parameter(Mandatory=$true)][string]$ReceiptSha256,
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
$payloadRoot = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs\Night Light\app'))
$receiptPath = Join-Path $payloadRoot 'OWNED-FILES.json'
$heldFiles = [Collections.Generic.List[object]]::new()
$mutex = [Threading.Mutex]::new($false, 'Local\HassTech.NightLight.PayloadUpdate')
$locked = $false
function Test-Mode {
    $sentinel=Join-Path $env:LOCALAPPDATA '.night-light-installer-test-root'
    return $env:NIGHT_LIGHT_INSTALL_TEST_MODE -ceq '1' -and (Test-Path -LiteralPath $sentinel)
}
function Desktop-Folder {
    if ($env:NIGHT_LIGHT_INSTALL_TEST_DESKTOP) {
        if (!(Test-Mode)) { throw 'Desktop override is allowed only in an isolated installer test root.' }
        return [IO.Path]::GetFullPath($env:NIGHT_LIGHT_INSTALL_TEST_DESKTOP)
    }
    return [Environment]::GetFolderPath('Desktop')
}
function Startup-Value {
    if ($env:NIGHT_LIGHT_INSTALL_TEST_STARTUP_FILE) {
        if (!(Test-Mode)) { throw 'Startup override is allowed only in an isolated installer test root.' }
        $path=[IO.Path]::GetFullPath($env:NIGHT_LIGHT_INSTALL_TEST_STARTUP_FILE)
        if (!$path.StartsWith([IO.Path]::GetFullPath($env:LOCALAPPDATA)+'\',[StringComparison]::OrdinalIgnoreCase)) {
            throw 'Startup test file escaped its isolated root.'
        }
        return $(if (Test-Path -LiteralPath $path) {[IO.File]::ReadAllText($path)} else {$null})
    }
    $runKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    return (Get-ItemProperty -LiteralPath $runKey -Name NightLightWidget -ErrorAction SilentlyContinue).NightLightWidget
}
function Remove-StartupValue {
    if ($env:NIGHT_LIGHT_INSTALL_TEST_STARTUP_FILE) {
        $path=[IO.Path]::GetFullPath($env:NIGHT_LIGHT_INSTALL_TEST_STARTUP_FILE)
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
        return
    }
    Remove-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name NightLightWidget -ErrorAction SilentlyContinue
}
function Get-StreamDigest($stream) {
    $stream.Position = 0
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Assert-NoLinks([string]$target) {
    $cursor = $target
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            if ((Get-Item -Force -LiteralPath $cursor).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Linked installation paths are not removed.'
            }
        }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
}
try {
    try { $locked=$mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $locked=$true }
    if (!$locked) { throw 'Another Night Light update or removal is running.' }
    if ($ReceiptSha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Invalid receipt identity.' }
    foreach ($process in Get-CimInstance Win32_Process) {
        if (($process.ExecutablePath -and $process.ExecutablePath.StartsWith($payloadRoot + '\',[StringComparison]::OrdinalIgnoreCase)) -or
            (!$process.ExecutablePath -and $process.Name -eq 'NightLight.exe')) {
            throw 'Close Night Light before removing its files. No process was stopped.'
        }
    }
    Assert-NoLinks $receiptPath
    $receiptStream = [IO.File]::Open($receiptPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Delete)
    $heldFiles.Add($receiptStream)
    if ($receiptStream.Length -gt 1048576 -or (Get-StreamDigest $receiptStream) -cne $ReceiptSha256) {
        throw 'Installation receipt changed. Nothing was removed.'
    }
    $receiptStream.Position = 0
    $reader = [IO.StreamReader]::new($receiptStream,[Text.Encoding]::UTF8,$true,4096,$true)
    try { $receipt = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
    if ($receipt.product_id -cne 'com.hasstech.night-light' -or $receipt.schema -ne 1 -or !$receipt.files.Count) {
        throw 'Unsupported installation receipt.'
    }
    $targets = [Collections.Generic.List[string]]::new()
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $receipt.files) {
        $relative = [string]$entry.path
        if (!$relative -or $relative.Contains('\') -or $relative.Contains(':') -or $relative.StartsWith('/') -or
            ($relative.Split('/') | Where-Object { $_ -eq '..' -or $_ -eq '.' -or !$_ -or $_ -ne $_.TrimEnd(' ','.') })) {
            throw 'Invalid owned-file path.'
        }
        $target = [IO.Path]::GetFullPath((Join-Path $payloadRoot $relative))
        if (!$target.StartsWith($payloadRoot + '\',[StringComparison]::OrdinalIgnoreCase) -or !$seen.Add($target)) {
            throw 'Owned-file target escaped or was repeated.'
        }
        Assert-NoLinks $target
        if (![IO.File]::Exists($target)) { continue } # Resume a partially completed removal.
        $stream = [IO.File]::Open($target,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Delete)
        $heldFiles.Add($stream)
        if ($stream.Length -ne $entry.size -or (Get-StreamDigest $stream) -cne $entry.sha256) {
            throw 'An installed file changed. Nothing was removed.'
        }
        $targets.Add($target)
    }
    # Every hash/lock check completes before the first deletion. Open handles
    # exclude new readers/writers while permitting these exact deletions.
    $shortcutsToRemove = [Collections.Generic.List[string]]::new()
    $shortcutFolders=@(
        (Desktop-Folder),
        (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'),
        (Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar')
    )
    $expectedTarget = Join-Path $payloadRoot 'NightLight.exe'
    $shell = New-Object -ComObject WScript.Shell
    foreach ($folder in $shortcutFolders) {
        foreach ($name in @('Night Light.lnk','Night Light Controls.lnk','Night Light by HT.lnk')) {
            $shortcutPath=Join-Path $folder $name
            if (!(Test-Path -LiteralPath $shortcutPath)) { continue }
            Assert-NoLinks $shortcutPath
            $shortcut = $shell.CreateShortcut($shortcutPath)
            if ($shortcut.TargetPath -and
                [IO.Path]::GetFullPath($shortcut.TargetPath).Equals($expectedTarget,[StringComparison]::OrdinalIgnoreCase) -and
                $shortcut.Arguments -cin @('--show','--toggle')) {
                $shortcutsToRemove.Add($shortcutPath)
            }
            [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
        }
    }
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
    $startupToRemove=(Startup-Value) -ceq ('"'+$expectedTarget+'" --background')
    if (!$VerifyOnly) {
        foreach ($shortcutPath in $shortcutsToRemove) { Remove-Item -LiteralPath $shortcutPath -Force }
        if ($startupToRemove) { Remove-StartupValue }
        foreach ($target in $targets) { Remove-Item -LiteralPath $target -Force }
        Remove-Item -LiteralPath $receiptPath -Force
        $statePath=Join-Path ([IO.Path]::GetDirectoryName($payloadRoot)) 'INSTALLATION.json'
        if (Test-Path -LiteralPath $statePath) {
            Assert-NoLinks $statePath
            $state=Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
            if ($state.product_id -ceq 'com.hasstech.night-light' -and $state.receipt_sha256 -ceq $ReceiptSha256 -and !$state.pending_cleanup.Count) {
                Remove-Item -LiteralPath $statePath -Force
            }
        }
    }
    Write-Output $(if ($VerifyOnly) {'Owned payload verified; no files removed.'} else {'Owned payload removed; preferences and unknown files retained.'})
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 2
} finally {
    foreach ($handle in $heldFiles) { $handle.Dispose() }
    if ($locked) { $mutex.ReleaseMutex() }; $mutex.Dispose()
}
