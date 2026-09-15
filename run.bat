@echo off
cd /d "%~dp0"

rem Python kojim se gradi okruzenje: onaj uz programe (Programi\python)
rem ima prednost pred sistemskim, da ga nadogradnja Windowsa ili Python
rem Managera ne moze razbiti. Ako ga nema, pada se natrag na "py -3.14".
set "PYEXE=%~dp0..\..\python\python.exe"
if not exist "%PYEXE%" set "PYEXE="

if exist ".env" goto venv
echo [QMS] Generiram .env (nasumicni tajni kljuc + admin lozinka)...
for /f %%i in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')"') do set "SK=%%i"
>.env echo SECRET_KEY=%SK%
>>.env echo ADMIN_PASSWORD=admin
>>.env echo # FIRMA_NAZIV=Puni naziv tvrtke d.o.o. (za PDF zaglavlja)
>>.env echo # Email obavijesti - ukloni # i popuni za slanje:
>>.env echo # NOTIF_ENABLED=true
>>.env echo # SMTP_HOST=smtp.gmail.com
>>.env echo # SMTP_PORT=587
>>.env echo # SMTP_USER=korisnik@gmail.com
>>.env echo # SMTP_PASSWORD=app-lozinka
>>.env echo # NOTIF_FROM=qms@firma.hr
>>.env echo # NOTIF_DEFAULT=kvaliteta@firma.hr

:venv
if not exist ".venv\Scripts\python.exe" goto build
.venv\Scripts\python.exe -c "import fastapi, uvicorn" 1>nul 2>nul
if errorlevel 1 goto rebuild
goto run

:rebuild
rem Prije brisanja provjeri da ima cime izgraditi novo okruzenje. Bez ove
rem provjere pokvaren Python znaci da ostanemo i bez postojeceg .venv-a.
if defined PYEXE ("%PYEXE%" -c "" 1>nul 2>nul) else (py -3.14 -c "" 1>nul 2>nul)
if errorlevel 1 goto nopy
echo [QMS] Postojeci .venv ne radi na ovom racunalu - ponovo gradim...
rmdir /s /q ".venv" 2>nul

:build
echo [QMS] Kreiram okruzenje i instaliram ovisnosti (jednom, ~1 min)...
if defined PYEXE ("%PYEXE%" -m venv .venv) else (py -3.14 -m venv .venv)
if errorlevel 1 goto nopy
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt

:run
echo.
echo [QMS] Pokrecem server na http://localhost:8601
echo Za prekid: CTRL+C pa zatvori prozor.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8601
echo.
echo Server je zaustavljen.
pause
goto :eof

:nopy
echo.
echo GRESKA: Python 3.14 nije pronadjen ("py -3.14" ne radi).
echo Postojece okruzenje NIJE dirano.
echo Instaliraj Python 3.14 (py install 3.14) pa pokreni run.bat ponovno.
echo.
rem Zapis ostaje na disku jer se kod autostarta ovaj prozor ne vidi.
> "run-greska.log" echo %DATE% %TIME% - "py -3.14" ne radi, okruzenje nije izgradjeno. .venv nije diran.
rem Cekanje umjesto "pause": skriveni prozor se sam zatvori i ne ostaje visjeti.
ping -n 61 127.0.0.1 >nul
