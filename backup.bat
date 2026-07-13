@echo off
cd /d "%~dp0"

if not exist "reklamacije.db" goto nodb
if not exist "backup" mkdir backup
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
copy /Y "reklamacije.db" "backup\reklamacije_%TS%.db" >nul
echo Backup spremljen: backup\reklamacije_%TS%.db
echo.
pause
goto :eof

:nodb
echo Baza reklamacije.db jos ne postoji - pokreni app barem jednom (run.bat).
echo.
pause
