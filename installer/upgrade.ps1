param(
    [Parameter(Mandatory=$true)][string]$IncomingRoot,
    [Parameter(Mandatory=$true)][string]$ReceiptSha256,
    [switch]$VerifyOnly,
    [string]$TestFailurePoint,
    [switch]$TestCrash
)
$ErrorActionPreference = 'Stop'
$installRoot = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs\Night Light'))
$appRoot = Join-Path $installRoot 'app'
$statePath = Join-Path $installRoot 'INSTALLATION.json'
$transactionPath = Join-Path $installRoot 'INSTALL-TRANSACTION.json'
$IncomingRoot = [IO.Path]::GetFullPath($IncomingRoot)
$held = [Collections.Generic.List[object]]::new()
$mutex = [Threading.Mutex]::new($false, 'Local\HassTech.NightLight.PayloadUpdate')
$locked = $false
$promoted = $false
$committed = $false
$previousApp = $null

function Assert-NoLinks([string]$path) {
    while ($path) {
        if ((Test-Path -LiteralPath $path) -and ((Get-Item -Force -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Linked installation paths are not supported.'
        }
        $path = [IO.Path]::GetDirectoryName($path)
    }
}
function Digest([string]$path) {
    $stream = [IO.File]::OpenRead($path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $sha.Dispose() }
}
function Read-Receipt([string]$root, [string]$expected) {
    $path = Join-Path $root 'OWNED-FILES.json'
    Assert-NoLinks $path
    if ($expected -cnotmatch '^[a-f0-9]{64}$' -or (Digest $path) -cne $expected) { throw 'Installation receipt did not match.' }
    if ((Get-Item -LiteralPath $path).Length -gt 1048576) { throw 'Oversized installation receipt.' }
    return Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
}
function Entries([string]$root, $receipt, [bool]$allowMissing=$false) {
    if ($receipt.schema -ne 1 -or $receipt.product_id -cne 'com.hasstech.night-light' -or !$receipt.files.Count) { throw 'Unrecognized Night Light payload.' }
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $receipt.files) {
        $relative = [string]$entry.path
        if (!$relative -or $relative.Contains('\') -or $relative.Contains(':') -or $relative.StartsWith('/') -or
            ($relative.Split('/') | Where-Object { !$_ -or $_ -eq '.' -or $_ -eq '..' -or $_ -ne $_.TrimEnd(' ','.') })) { throw 'Invalid payload path.' }
        $path = [IO.Path]::GetFullPath((Join-Path $root $relative))
        if (!$path.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or !$seen.Add($path)) { throw 'Payload path escaped or was repeated.' }
        Assert-NoLinks $path
        if (!(Test-Path -LiteralPath $path) -and $allowMissing) { continue }
        if ((Get-Item -LiteralPath $path).Length -ne $entry.size -or (Digest $path) -cne $entry.sha256) { throw "Installed file changed: $relative. Replacement stopped." }
        [pscustomobject]@{path=$path;relative=$relative;sha256=$entry.sha256;size=$entry.size}
    }
    if (!$seen.Contains((Join-Path $root 'NightLight.exe'))) { throw 'Payload has no application.' }
}
function Write-State($value) {
    Write-AtomicJson $statePath $value
}
function Write-AtomicJson([string]$path,$value) {
    $temp = $path + '.tmp'
    Assert-NoLinks $temp
    if (Test-Path -LiteralPath $temp) { throw 'A previous installation state write needs recovery.' }
    [IO.File]::WriteAllText($temp, ($value | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))
    $stream=[IO.File]::Open($temp,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    try { $stream.Flush($true) } finally { $stream.Dispose() }
    if (Test-Path -LiteralPath $path) { [IO.File]::Replace($temp,$path,[NullString]::Value) }
    else { [IO.File]::Move($temp,$path) }
}
function Write-Transaction($value) {
    Write-AtomicJson $transactionPath $value
}
function Invoke-TestFailure([string]$point) {
    if (!$TestFailurePoint -or $TestFailurePoint -cne $point) { return }
    $sentinel=Join-Path ([IO.Path]::GetDirectoryName([IO.Path]::GetDirectoryName($installRoot))) '.night-light-installer-test-root'
    if ($env:NIGHT_LIGHT_INSTALL_TEST_MODE -cne '1' -or !(Test-Path -LiteralPath $sentinel)) {
        throw 'Installer failure injection is confined to an explicit isolated test root.'
    }
    if ($TestCrash) { exit 91 }
    throw "Injected installer failure at $point."
}
function Read-Transaction {
    if (!(Test-Path -LiteralPath $transactionPath)) { return $null }
    Assert-NoLinks $transactionPath
    if ((Get-Item -LiteralPath $transactionPath).Length -gt 4MB) { throw 'Oversized installation transaction record.' }
    $journal=Get-Content -Raw -LiteralPath $transactionPath | ConvertFrom-Json
    if ($journal.schema -ne 1 -or $journal.product_id -cne 'com.hasstech.night-light' -or
        $journal.phase -cnotin @('prepared','previous_reserved','replacement_promoted','integration_updated','committed')) {
        throw 'Unrecognized installation transaction record.'
    }
    return $journal
}
function Remove-JournalPayload($journal) {
    if (!(Test-Path -LiteralPath $appRoot)) { return }
    foreach ($entry in $journal.new_receipt.files) {
        $relative=[string]$entry.path
        if (!$relative -or $relative.Contains('\') -or $relative.Contains(':') -or $relative.StartsWith('/') -or
            ($relative.Split('/') | Where-Object { !$_ -or $_ -eq '.' -or $_ -eq '..' -or $_ -ne $_.TrimEnd(' ','.') })) {
            throw 'Invalid recovery payload path.'
        }
        $target=[IO.Path]::GetFullPath((Join-Path $appRoot $relative))
        if (!$target.StartsWith($appRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Recovery payload path escaped.' }
        Assert-NoLinks $target
        if (Test-Path -LiteralPath $target) {
            if ((Get-Item -LiteralPath $target).Length -ne $entry.size -or (Digest $target) -cne $entry.sha256) {
                throw 'A replacement file changed during interrupted-install recovery.'
            }
            Remove-Item -LiteralPath $target -Force
        }
    }
    $newReceipt=Join-Path $appRoot 'OWNED-FILES.json'
    if (Test-Path -LiteralPath $newReceipt) {
        if ((Digest $newReceipt) -cne $journal.new_receipt_sha256) { throw 'The replacement receipt changed during recovery.' }
        Remove-Item -LiteralPath $newReceipt -Force
    }
    Get-ChildItem -LiteralPath $appRoot -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object {
        if (!(Get-ChildItem -Force -LiteralPath $_.FullName)) { [IO.Directory]::Delete($_.FullName) }
    }
    if (!(Get-ChildItem -Force -LiteralPath $appRoot)) { [IO.Directory]::Delete($appRoot); return }
    if (Get-ChildItem -LiteralPath $appRoot -File -Filter '*.exe' -Recurse) {
        throw 'An unknown executable prevents interrupted-install recovery.'
    }
    $quarantine=Join-Path $installRoot ('.interrupted-data-'+[Guid]::NewGuid().ToString('N'))
    Move-Item -LiteralPath $appRoot -Destination $quarantine
}
function Restore-JournalIntegrations($journal) {
    $shell=New-Object -ComObject WScript.Shell
    $expected=Join-Path $appRoot 'NightLight.exe'
    foreach ($item in @($journal.links)) {
        $path=[IO.Path]::GetFullPath([string]$item.path)
        Assert-NoLinks $path
        if ($item.existed) {
            $prior=[Convert]::FromBase64String([string]$item.bytes)
            if ((Test-Path -LiteralPath $path) -and [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) -eq $item.bytes) { continue }
            if (Test-Path -LiteralPath $path) {
                $link=$shell.CreateShortcut($path)
                if (![IO.Path]::GetFullPath($link.TargetPath).Equals($expected,[StringComparison]::OrdinalIgnoreCase)) {
                    throw 'A shortcut changed during interrupted-install recovery.'
                }
            }
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path))
            [IO.File]::WriteAllBytes($path,$prior)
        } elseif (Test-Path -LiteralPath $path) {
            $link=$shell.CreateShortcut($path)
            if ([IO.Path]::GetFullPath($link.TargetPath).Equals($expected,[StringComparison]::OrdinalIgnoreCase)) {
                Remove-Item -LiteralPath $path -Force
            } else { throw 'A newly occupied shortcut path prevents recovery.' }
        }
    }
    $runKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    $current=(Get-ItemProperty -LiteralPath $runKey -Name NightLightWidget -ErrorAction SilentlyContinue).NightLightWidget
    $newValue='"'+$expected+'" --background'
    if ($current -eq $newValue) {
        if ($journal.startup.existed) { Set-ItemProperty -LiteralPath $runKey -Name NightLightWidget -Value ([string]$journal.startup.value) }
        else { Remove-ItemProperty -LiteralPath $runKey -Name NightLightWidget -ErrorAction SilentlyContinue }
    } elseif ($journal.startup.existed -and $current -ne [string]$journal.startup.value) {
        throw 'The startup entry changed during interrupted-install recovery.'
    }
}
function Recover-Transaction {
    $journal=Read-Transaction
    if ($null -eq $journal) { return }
    if ($journal.phase -eq 'committed') {
        if (!(Test-Path -LiteralPath $statePath)) { throw 'Committed replacement has no installation state.' }
        $state=Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
        if ($state.product_id -cne 'com.hasstech.night-light' -or $state.receipt_sha256 -cne $journal.new_receipt_sha256) {
            throw 'Committed replacement identity does not match its recovery record.'
        }
        Remove-Item -LiteralPath $transactionPath -Force
        return
    }
    if ($journal.phase -eq 'prepared') {
        # No payload or integration mutation occurs before this phase marker.
        # The old app (if any) is still in its original location.
        Remove-Item -LiteralPath $transactionPath -Force
        return
    }
    Restore-JournalIntegrations $journal
    Remove-JournalPayload $journal
    if ($journal.previous_directory) {
        if ([string]$journal.previous_directory -cnotmatch '^\.previous-[a-f0-9]{32}$') { throw 'Invalid previous payload recovery path.' }
        $prior=Join-Path $installRoot ([string]$journal.previous_directory)
        if (!(Test-Path -LiteralPath $prior)) { throw 'Previous payload is missing during recovery.' }
        $null=@(Entries $prior $journal.previous_receipt)
        if (Test-Path -LiteralPath $appRoot) { throw 'Recovered app destination is not empty.' }
        Move-Item -LiteralPath $prior -Destination $appRoot
    }
    Remove-Item -LiteralPath $transactionPath -Force
}
function Owned-Processes($targets) {
    @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $targets.Contains($_.ExecutablePath) })
}
function Reset-Display {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class NightLightUpgradeDisplay {
 [DllImport("Magnification.dll")] static extern bool MagInitialize();
 [DllImport("Magnification.dll")] static extern bool MagUninitialize();
 [DllImport("Magnification.dll")] static extern bool MagSetFullscreenColorEffect([In] float[] matrix);
 [DllImport("Magnification.dll")] static extern bool MagGetFullscreenColorEffect([Out] float[] matrix);
 public static void Restore() {
  if (!MagInitialize()) throw new Exception("Display reset could not initialize.");
  try {
   var neutral=new float[25]; for(int n=0;n<5;n++) neutral[n*6]=1;
   if(!MagSetFullscreenColorEffect(neutral)) throw new Exception("Display reset was refused.");
   var actual=new float[25];
   if(!MagGetFullscreenColorEffect(actual)) throw new Exception("Display reset could not be verified.");
   for(int n=0;n<25;n++) if(Math.Abs(actual[n]-neutral[n])>0.00001) throw new Exception("Display reset did not match.");
  } finally { MagUninitialize(); }
 }
}
'@
    [NightLightUpgradeDisplay]::Restore()
}
try {
    try { $locked=$mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $locked=$true }
    if (!$locked) { throw 'Another Night Light update is running.' }
    Assert-NoLinks $installRoot
    Assert-NoLinks $IncomingRoot
    Recover-Transaction
    if ($IncomingRoot.Equals($installRoot,[StringComparison]::OrdinalIgnoreCase) -or $IncomingRoot.StartsWith($installRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Incoming payload must be staged outside the installation.' }
    $incomingReceipt=Read-Receipt $IncomingRoot $ReceiptSha256
    $incomingEntries=@(Entries $IncomingRoot $incomingReceipt)
    $old=[Collections.Generic.List[object]]::new()
    $catalog=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'legacy-installations.json') | ConvertFrom-Json
    $state=$null
    if (Test-Path -LiteralPath $statePath) {
        Assert-NoLinks $statePath
        $state=Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
        if ($state.product_id -cne 'com.hasstech.night-light' -or $state.schema -ne 1) { throw 'Unrecognized installation state.' }
    }
    if (Test-Path -LiteralPath $appRoot) {
        if (!$state) { throw 'Existing app has no verified installation record.' }
        $receipt=Read-Receipt $appRoot $state.receipt_sha256
        $old.Add([pscustomobject]@{root=$appRoot;receipt=$receipt;receipt_sha256=$state.receipt_sha256})
    }
    foreach ($item in $catalog.installations) {
        if ($item.directory -cnotmatch '^[a-f0-9]{40}$') { throw 'Invalid legacy catalog directory.' }
        $root=Join-Path $installRoot $item.directory
        if (Test-Path -LiteralPath $root) { $old.Add([pscustomobject]@{root=$root;receipt=$item;receipt_sha256=$null}) }
    }
    foreach ($pending in $state.pending_cleanup) {
        if ($pending.directory -cnotmatch '^(?:[a-f0-9]{40}|\.previous-[a-f0-9]{32})$') { throw 'Invalid cleanup journal directory.' }
        $root=Join-Path $installRoot $pending.directory
        if ((Test-Path -LiteralPath $root) -and !($old | Where-Object root -eq $root)) {
            $old.Add([pscustomobject]@{root=$root;receipt=$pending.receipt;receipt_sha256=$pending.receipt_sha256})
        }
    }
    foreach ($item in $old) { $null=@(Entries $item.root $item.receipt ($item.root -ne $appRoot)) }
    # Unknown executable installations stop replacement rather than silently
    # allowing two independently launchable app versions.
    if (Test-Path -LiteralPath $installRoot) {
        foreach ($dir in Get-ChildItem -LiteralPath $installRoot -Directory) {
            if ((Test-Path -LiteralPath (Join-Path $dir.FullName 'NightLight.exe')) -and !($old | Where-Object root -eq $dir.FullName)) { throw 'An unrecognized Night Light copy needs identification before replacement.' }
        }
    }
    $targets=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($item in $old) { [void]$targets.Add((Join-Path $item.root 'NightLight.exe')) }
    $links=[Collections.Generic.List[object]]::new()
    $shell=New-Object -ComObject WScript.Shell
    $desktopFolder=[Environment]::GetFolderPath('Desktop')
    $startFolder=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    $pinnedFolder=Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'
    $linkSpecs=@(
        @{path=(Join-Path $desktopFolder 'Night Light.lnk');arguments='--show';description='Open Night Light controls';required=$false},
        @{path=(Join-Path $desktopFolder 'Night Light by HT.lnk');arguments='--show';description='Open Night Light controls';required=$false},
        @{path=(Join-Path $startFolder 'Night Light.lnk');arguments='--toggle';description='Turn Night Light on or off';required=$true},
        @{path=(Join-Path $startFolder 'Night Light Controls.lnk');arguments='--show';description='Open Night Light controls';required=$true},
        @{path=(Join-Path $startFolder 'Night Light by HT.lnk');arguments='--toggle';description='Turn Night Light on or off';required=$false},
        @{path=(Join-Path $pinnedFolder 'Night Light.lnk');arguments='--toggle';description='Turn Night Light on or off';required=$false},
        @{path=(Join-Path $pinnedFolder 'Night Light by HT.lnk');arguments='--toggle';description='Turn Night Light on or off';required=$false}
    )
    foreach ($spec in $linkSpecs) {
        $path=$spec.path
        if (Test-Path -LiteralPath $path) {
            Assert-NoLinks $path
            $link=$shell.CreateShortcut($path)
            if ($targets.Contains($link.TargetPath) -or $link.TargetPath -eq (Join-Path $appRoot 'NightLight.exe')) {
                $links.Add([pscustomobject]@{path=$path;bytes=[IO.File]::ReadAllBytes($path);arguments=$spec.arguments;description=$spec.description})
            } elseif ($spec.required) { throw 'A required Start shortcut belongs to another target.' }
        }
    }
    if ($VerifyOnly) { Write-Output "Replacement preflight passed: $($old.Count) recognized previous payload(s)."; exit 0 }
    $running=@(Owned-Processes $targets)
    if ($running.Count) {
        $client=Start-Process -FilePath (Join-Path $IncomingRoot 'NightLight.exe') -ArgumentList '--request-exit' -WindowStyle Hidden -PassThru
        if (!$client.WaitForExit(10000)) { $client.Kill(); $client.WaitForExit() }
        $deadline=[DateTime]::UtcNow.AddSeconds(5)
        while ((Owned-Processes $targets).Count -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
        $running=@(Owned-Processes $targets)
        if ($running.Count) {
            # Compatibility path: only exact, hash-verified app executables.
            # Capture their embedded UI children before their parent exits.
            $ids=@($running | ForEach-Object ProcessId)
            $children=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'NightLight.Premium.exe' -and $ids -contains $_.ParentProcessId })
            try {
                foreach ($proc in $running) {
                    $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ProcessId)"
                    if ($live -and $live.CreationDate -eq $proc.CreationDate -and $targets.Contains($live.ExecutablePath)) { Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue }
                }
                foreach ($proc in $children) {
                    $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ProcessId)"
                    if ($live -and $live.CreationDate -eq $proc.CreationDate -and $live.ExecutablePath -eq $proc.ExecutablePath) { Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue }
                }
                $deadline=[DateTime]::UtcNow.AddSeconds(5)
                while ((Owned-Processes $targets).Count -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
                if ((Owned-Processes $targets).Count) { throw 'The previous app did not exit.' }
            } finally { Reset-Display }
        }
    }
    # Windows may retain executable handles briefly after process exit. Retry
    # sharing violations for a bounded interval, before any payload mutation.
    $lockDeadline=[DateTime]::UtcNow.AddSeconds(5)
    while ($true) {
        try {
            foreach ($item in $old) {
                foreach ($entry in @(Entries $item.root $item.receipt ($item.root -ne $appRoot))) {
                    $stream=[IO.File]::Open($entry.path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Delete)
                    $held.Add($stream)
                    $sha=[Security.Cryptography.SHA256]::Create()
                    try { $digest=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
                    finally { $sha.Dispose() }
                    if ($digest -cne $entry.sha256 -or $stream.Length -ne $entry.size) { throw 'An owned file changed before locking.' }
                }
            }
            break
        } catch {
            foreach ($handle in $held) { $handle.Dispose() }; $held.Clear()
            if ($_.Exception.GetBaseException() -isnot [IO.IOException] -or [DateTime]::UtcNow -ge $lockDeadline) { throw }
            Start-Sleep -Milliseconds 200
        }
    }
    [void][IO.Directory]::CreateDirectory($installRoot)
    $currentOld=$old | Where-Object root -eq $appRoot | Select-Object -First 1
    $plannedPrevious=$(if ($currentOld) { '.previous-'+[Guid]::NewGuid().ToString('N') } else { $null })
    $journalLinks=[Collections.Generic.List[object]]::new()
    foreach ($item in $links) { $journalLinks.Add(@{path=$item.path;existed=$true;bytes=[Convert]::ToBase64String($item.bytes)}) }
    foreach ($spec in $linkSpecs) {
        if ($spec.required -and !(Test-Path -LiteralPath $spec.path)) {
            $journalLinks.Add(@{path=$spec.path;existed=$false;bytes=$null})
        }
    }
    $runKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    $startup=(Get-ItemProperty -LiteralPath $runKey -Name NightLightWidget -ErrorAction SilentlyContinue).NightLightWidget
    $journal=@{schema=1;product_id='com.hasstech.night-light';transaction_id=[Guid]::NewGuid().ToString('N');phase='prepared';
        new_receipt_sha256=$ReceiptSha256;new_receipt=$incomingReceipt;previous_directory=$plannedPrevious;
        previous_receipt=$(if ($currentOld) {$currentOld.receipt}else{$null});links=@($journalLinks);
        startup=@{existed=$null -ne $startup;value=$startup}}
    Write-Transaction $journal
    Invoke-TestFailure 'prepared'
    if (Test-Path -LiteralPath $appRoot) {
        $previousApp=Join-Path $installRoot $plannedPrevious
        Move-Item -LiteralPath $appRoot -Destination $previousApp
        ($old | Where-Object root -eq $appRoot).root=$previousApp
    }
    $journal.phase='previous_reserved';Write-Transaction $journal
    Invoke-TestFailure 'previous_reserved'
    # Copy only verified payload entries; unrelated staging contents cannot ship.
    [void][IO.Directory]::CreateDirectory($appRoot)
    $promoted=$true
    foreach ($entry in $incomingEntries) {
        $target=Join-Path $appRoot $entry.relative
        [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
        [IO.File]::Copy($entry.path,$target,$false)
    }
    [IO.File]::Copy((Join-Path $IncomingRoot 'OWNED-FILES.json'),(Join-Path $appRoot 'OWNED-FILES.json'),$false)
    $null=@(Entries $appRoot (Read-Receipt $appRoot $ReceiptSha256))
    $journal.phase='replacement_promoted';Write-Transaction $journal
    Invoke-TestFailure 'replacement_promoted'
    for ($linkIndex=0; $linkIndex -lt $links.Count; $linkIndex++) {
        $item=$links[$linkIndex]
        $link=$shell.CreateShortcut($item.path)
        $link.TargetPath=Join-Path $appRoot 'NightLight.exe'
        $link.WorkingDirectory=$appRoot
        $link.IconLocation=$link.TargetPath
        $link.Arguments=$item.arguments
        $link.Description=$item.description
        $link.Save()
    }
    foreach ($spec in $linkSpecs) {
        if (!$spec.required -or (Test-Path -LiteralPath $spec.path)) { continue }
        [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($spec.path))
        $link=$shell.CreateShortcut($spec.path); $link.TargetPath=Join-Path $appRoot 'NightLight.exe'
        $link.Arguments=$spec.arguments;$link.Description=$spec.description
        $link.WorkingDirectory=$appRoot;$link.IconLocation=$link.TargetPath;$link.Save()
    }
    foreach ($target in $targets) {
        if ($startup -eq ('"'+$target+'" --background')) {
            Set-ItemProperty -LiteralPath $runKey -Name NightLightWidget -Value ('"'+(Join-Path $appRoot 'NightLight.exe')+'" --background')
        }
    }
    $journal.phase='integration_updated';Write-Transaction $journal
    Invoke-TestFailure 'integration_updated'
    $pending=@($old | ForEach-Object { @{directory=[IO.Path]::GetFileName($_.root);receipt=$_.receipt;receipt_sha256=$_.receipt_sha256} })
    $newState=@{schema=1;product_id='com.hasstech.night-light';receipt_sha256=$ReceiptSha256;pending_cleanup=$pending}
    Write-State $newState
    $committed=$true
    $journal.phase='committed';Write-Transaction $journal
    Invoke-TestFailure 'committed'
    foreach ($item in $old) {
        foreach ($entry in $item.receipt.files) {
            $path=Join-Path $item.root $entry.path
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
        }
        $receiptPath=Join-Path $item.root 'OWNED-FILES.json'
        if ($item.receipt_sha256 -and (Test-Path -LiteralPath $receiptPath)) {
            if ((Digest $receiptPath) -cne $item.receipt_sha256) { throw 'Previous receipt changed during cleanup.' }
            Remove-Item -LiteralPath $receiptPath -Force
        }
    }
    foreach ($handle in $held) { $handle.Dispose() }; $held.Clear()
    foreach ($item in $old) {
        # Empty directories only; unrelated files are never recursively removed.
        Get-ChildItem -LiteralPath $item.root -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object {
            if (!(Get-ChildItem -Force -LiteralPath $_.FullName)) { [IO.Directory]::Delete($_.FullName) }
        }
        if (!(Get-ChildItem -Force -LiteralPath $item.root)) { [IO.Directory]::Delete($item.root) }
    }
    $newState.pending_cleanup=@()
    Write-State $newState
    Remove-Item -LiteralPath $transactionPath -Force
    Write-Output 'Night Light replaced. Previous verified app files removed; shortcuts updated and preferences retained.'
    exit 0
} catch {
    $failure=$_
    # Before commit, return existing shortcuts and payload to their old location.
    foreach ($handle in $held) { $handle.Dispose() }; $held.Clear()
    if (!$committed) {
        if (Test-Path -LiteralPath $transactionPath) { Recover-Transaction }
        else {
            if ($links) { foreach ($item in $links) { [IO.File]::WriteAllBytes($item.path,$item.bytes) } }
            if ($previousApp -and (Test-Path -LiteralPath $previousApp) -and !(Test-Path -LiteralPath $appRoot)) {
                Move-Item -LiteralPath $previousApp -Destination $appRoot
            }
        }
    }
    $failureText=$failure.ToString()+[Environment]::NewLine+$failure.ScriptStackTrace
    # A persistent diagnostic survives NSIS temporary-directory cleanup.
    try {
        $errorPath=Join-Path $env:LOCALAPPDATA 'NightLight-setup-error.txt'
        Assert-NoLinks $errorPath
        [IO.File]::WriteAllText($errorPath,$failureText)
    } catch { }
    Write-Error $failure -ErrorAction Continue
    exit 2
} finally {
    foreach ($handle in $held) { $handle.Dispose() }
    if ($locked) { $mutex.ReleaseMutex() }; $mutex.Dispose()
}
