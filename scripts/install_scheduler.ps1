<#
.SYNOPSIS
  为 PersonalQuant 注册 Windows 计划任务：每个交易日收盘后跑数据更新 + paper live。

.DESCRIPTION
  默认是 dry-run：只打印将要创建的任务，不实际注册。真正注册需要显式加 -Apply。

  纪律（spec §44 / §13）：
    - 只做「数据更新 -> paper live -> 告警」三步，绝不连接券商、绝不下单。
    - 权限不足时不要反复改系统权限：保持 dry-run、手动跑 run_daily.py 即可。
      脚本本身就是可复现的配置记录。

  实现说明：不把长命令塞进计划任务的 -Argument（多层引号转义极易出错），
  而是生成一个 launcher .cmd，计划任务只负责调用它。

.PARAMETER Apply
  真正注册计划任务（不加则只预览）。

.PARAMETER Time
  每天的触发时间，默认 18:30（收盘后，数据源通常已更新）。

.PARAMETER TaskName
  任务名，默认 PersonalQuant-PaperLive。

.EXAMPLE
  powershell -File scripts/install_scheduler.ps1
  powershell -File scripts/install_scheduler.ps1 -Apply
#>
[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$Time = "18:30",
    [string]$TaskName = "PersonalQuant-PaperLive"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Launcher = Join-Path $Root "scripts\run_paper_live_daily.cmd"

if (-not (Test-Path $Python)) {
    Write-Error "找不到虚拟环境 Python：$Python（先建 .venv）"
    exit 1
}

# 三步：先更新数据，再跑 paper live，最后看告警。
# 数据更新失败也继续 —— 一次网络抖动不该让整天的观测丢掉。
$steps = @(
    @{ Name = "refresh"; Args = "scripts\quant\refresh_all.py --continue-on-error" },
    @{ Name = "paper";   Args = "scripts\paper_live\run_daily.py" },
    @{ Name = "alerts";  Args = "scripts\paper_live\check_alerts.py" }
)

Write-Host "PersonalQuant paper live scheduler"
Write-Host "  project root : $Root"
Write-Host "  python       : $Python"
Write-Host "  launcher     : $Launcher"
Write-Host "  task name    : $TaskName"
Write-Host "  trigger      : daily $Time"
if ($Apply) {
    Write-Host "  mode         : APPLY (will register)"
} else {
    Write-Host "  mode         : DRY-RUN (preview only)"
}
Write-Host ""
Write-Host "steps:"
foreach ($step in $steps) {
    Write-Host ("  [{0,-8}] python {1}" -f $step.Name, $step.Args)
}
Write-Host ""
Write-Host "never does: broker API, auto order, real money."

# launcher 内容（四处都只用单引号，避免嵌套转义）
$lines = @("@echo off", "chcp 65001 >nul", "cd /d `"$Root`"")
foreach ($step in $steps) {
    $lines += "`"$Python`" $($step.Args)"
}
$lines += "exit /b 0"

if ($Apply) {
    Set-Content -Path $Launcher -Value $lines -Encoding UTF8
    Write-Host ""
    Write-Host "wrote launcher: $Launcher"
}

Write-Host ""
if (-not $Apply) {
    Write-Host "DRY-RUN: nothing was changed. Add -Apply to register."
    Write-Host ""
    Write-Host "launcher that would be written to $Launcher :"
    foreach ($line in $lines) { Write-Host "  $line" }
    Write-Host ""
    Write-Host "manual equivalent:"
    Write-Host "  cd '$Root'"
    foreach ($step in $steps) { Write-Host "  & '$Python' $($step.Args)" }
    exit 0
}

$taskAction = New-ScheduledTaskAction -Execute $Launcher
$taskTrigger = New-ScheduledTaskTrigger -Daily -At $Time
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 2)

try {
    Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Force | Out-Null
    Write-Host "registered scheduled task: $TaskName"
    Write-Host "inspect : Get-ScheduledTask -TaskName $TaskName"
    Write-Host "remove  : Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
} catch {
    Write-Host "registration failed: $_"
    Write-Host "If it is a permission issue, do NOT keep changing system policy."
    Write-Host "Stay on dry-run and run run_daily.py manually."
    exit 2
}
