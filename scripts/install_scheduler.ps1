<#
.SYNOPSIS
  注册 Windows 计划任务 PersonalQuant-Daily：每工作日收盘后跑一次每日流水线。

.DESCRIPTION
  默认 **dry-run**：只打印将要创建的任务，不实际注册。真正注册需 -Apply。

  纪律（spec §25 / §26）：
    - 只跑 `python scripts/run_daily.py`，**绝不连接券商、绝不下单**。
    - **绝不修改 PowerShell 执行策略**。系统策略禁止运行脚本时，
      不要 Set-ExecutionPolicy、不要绕过安全策略 ——
      保持 dry-run、手动跑 run_daily.py 即可，状态记 SCHEDULER_NOT_INSTALLED。
    - 不假设电脑一直开机：任务用 StartWhenAvailable，错过的时间点
      在下次开机后补跑，补跑用**实际最新交易日**（由 run_daily 自己决定）。

.PARAMETER Apply
  真正注册计划任务（不加则只预览）。

.PARAMETER Time
  触发时间，默认 18:30（收盘后，数据源通常已更新）。

.PARAMETER TaskName
  任务名，默认 PersonalQuant-Daily。

.EXAMPLE
  powershell -File scripts/install_scheduler.ps1
  powershell -File scripts/install_scheduler.ps1 -Apply
#>
[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$Time = "18:30",
    [string]$TaskName = "PersonalQuant-Daily"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Launcher = Join-Path $Root "scripts\run_daily.cmd"

if (-not (Test-Path $Python)) {
    Write-Error "找不到虚拟环境 Python：$Python（先建 .venv）"
    exit 1
}

Write-Host "PersonalQuant daily pipeline scheduler"
Write-Host "  project root : $Root"
Write-Host "  python       : $Python"
Write-Host "  task name    : $TaskName"
Write-Host "  trigger      : weekdays $Time"
if ($Apply) {
    Write-Host "  mode         : APPLY (will register)"
} else {
    Write-Host "  mode         : DRY-RUN (preview only)"
}
Write-Host ""
Write-Host "runs: python scripts/run_daily.py"
Write-Host "never does: broker API, auto order, model retraining, factor selection."
Write-Host "never changes the PowerShell execution policy."

# launcher 内容（只用单引号，避免嵌套转义）
$lines = @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$Root`"",
    "`"$Python`" scripts\run_daily.py",
    "exit /b %ERRORLEVEL%"
)

if ($Apply) {
    Set-Content -Path $Launcher -Value $lines -Encoding UTF8
    Write-Host ""
    Write-Host "wrote launcher: $Launcher"
}

Write-Host ""
if (-not $Apply) {
    Write-Host "DRY-RUN: nothing changed. Add -Apply to register."
    Write-Host ""
    Write-Host "launcher that would be written to $Launcher :"
    foreach ($line in $lines) { Write-Host "  $line" }
    Write-Host ""
    Write-Host "manual equivalent:"
    Write-Host "  cd '$Root'"
    Write-Host "  & '$Python' scripts\run_daily.py"
    exit 0
}

$taskAction = New-ScheduledTaskAction -Execute $Launcher
# 工作日（周一至周五）。节假日由 run_daily 自己识别为"非交易日"。
$taskTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $Time
# StartWhenAvailable：错过的时间点在下次开机后补跑（不假设一直开机）
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 2)

try {
    Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Force | Out-Null
    Write-Host "registered scheduled task: $TaskName"
    Write-Host "inspect : Get-ScheduledTask -TaskName $TaskName"
    Write-Host "remove  : powershell -File scripts/uninstall_scheduler.ps1 -Apply"
} catch {
    Write-Host "registration failed: $_"
    Write-Host "Do NOT change the PowerShell execution policy to work around this."
    Write-Host "Stay on dry-run and run run_daily.py manually; status is recorded as"
    Write-Host "SCHEDULER_NOT_INSTALLED."
    exit 2
}
