@echo off
echo ==============================================
echo    Deteniendo instancias de PERRA_JARVIS...
echo ==============================================
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Detenido proceso Jarvis PID:' $_.ProcessId }"
echo Finalizado.
timeout /t 2 >nul
