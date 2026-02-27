# Установка Job Finder в Windows Task Scheduler
# Запускать ОДИН РАЗ от имени администратора (или текущего пользователя)
# После установки задача будет запускаться каждый день в 09:00

$TaskName   = "JobFinderDaily"
$ScriptPath = "C:\Users\kenih\OneDrive\Рабочий стол\Job_finder\run_local.ps1"
$RunTime    = "09:00"

# Проверить что скрипт существует
if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: $ScriptPath not found!" -ForegroundColor Red
    exit 1
}

# Удалить старую задачу если есть
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Removing existing task '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Что запускать: powershell.exe -File run_local.ps1 -ExecutionPolicy Bypass
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$ScriptPath`""

# Когда запускать: каждый день в 09:00
$Trigger = New-ScheduledTaskTrigger -Daily -At $RunTime

# Настройки: запускать даже если не в сети, не прерывать при входе/выходе
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -WakeToRun:$false

# Зарегистрировать задачу для текущего пользователя
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Limited `
    -Force | Out-Null

Write-Host ""
Write-Host "Task '$TaskName' registered successfully!" -ForegroundColor Green
Write-Host "  Schedule : Every day at $RunTime" -ForegroundColor Cyan
Write-Host "  Script   : $ScriptPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run immediately for testing:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Yellow
Write-Host "  notepad `"C:\Users\kenih\OneDrive\Рабочий стол\Job_finder\logs\local_run.log`"" -ForegroundColor White
Write-Host ""
Write-Host "To remove the task:" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor White
