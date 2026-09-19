<#
.SYNOPSIS
  卸载 Windows 计划任务 PersonalQuant-Daily。

.DESCRIPTION
  默认 **dry-run**：只显示将要删除的任务。真正删除需 -Apply。

  同样**不修改 PowerShell 执行策略**（spec §26）。

.EXAMPLE
  powershell -File scripts/uninstall_scheduler.ps1
  powershell -File scripts/uninstall_scheduler.ps1 -Apply
#>
[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$TaskName = "PersonalQuant-Daily"
)

$ErrorActionPreference = "Stop"

Write-Host "PersonalQuant scheduler uninstall"
Write-Host "  task name : $TaskName"
if ($Apply) { Write-Host "  mode      : APPLY (will remove)" }
else { Write-Host "  mode      : DRY-RUN (preview only)" }
Write-Host ""

$exists = $false
try {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $exists = $true
    Write-Host "found task: $($t.TaskName)  state=$($t.State)"
} catch {
    Write-Host "task not found: $TaskName"
}

if (-not $Apply) {
    Write-Host ""
    if ($exists) {
        Write-Host "DRY-RUN: nothing removed. Add -Apply to unregister."
    } else {
        Write-Host "nothing to do."
    }
    exit 0
}

if (-not $exists) { exit 0 }
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "unregistered: $TaskName"
    Write-Host "The daily pipeline can still be run manually:"
    Write-Host "  python scripts/run_daily.py"
} catch {
    Write-Host "uninstall failed: $_"
    exit 2
}
