@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto nov
.venv\Scripts\python.exe provjeri_rokove.py
goto kraj
:nov
echo GRESKA: okruzenje nije postavljeno. Prvo pokreni run.bat jednom.
:kraj
