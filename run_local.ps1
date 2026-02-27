# Job Finder - Local Runner
# Запускается вручную или через Windows Task Scheduler
# Скрипт автоматически пишет лог в logs/local_run.log

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe  = "C:\Users\kenih\AppData\Local\Programs\Python\Python313\python.exe"
$LogDir     = Join-Path $ProjectDir "logs"
$LogFile    = Join-Path $LogDir "local_run.log"

# Создать папку логов если нет
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content $LogFile ""
Add-Content $LogFile "============================================"
Add-Content $LogFile "[$Timestamp] Starting Job Finder (local run)"
Add-Content $LogFile "============================================"

# Перейти в папку проекта
Set-Location $ProjectDir

# Установить переменные окружения
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH       = $ProjectDir
$env:LOG_LEVEL        = "INFO"

# Запустить пайплайн
Write-Host "[$Timestamp] Job Finder started..." -ForegroundColor Cyan

try {
    & $PythonExe main.py --export-sheets --top-n 20 2>&1 | Tee-Object -Append -FilePath $LogFile
    $ExitCode = $LASTEXITCODE

    if ($ExitCode -eq 0) {
        $Done = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content $LogFile "[$Done] Job Finder completed successfully"
        Write-Host "[$Done] Done! Check Google Sheets." -ForegroundColor Green
    } else {
        $Done = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content $LogFile "[$Done] Job Finder exited with code $ExitCode"
        Write-Host "[$Done] Finished with errors (exit code $ExitCode)" -ForegroundColor Yellow
    }
} catch {
    $Err = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content $LogFile "[$Err] FATAL ERROR: $_"
    Write-Host "[$Err] Fatal error: $_" -ForegroundColor Red
}
