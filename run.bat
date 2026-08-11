@echo off
cd /d "%~dp0"

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
echo [QMS] Postojeci .venv ne radi na ovom racunalu - ponovo gradim...
rmdir /s /q ".venv" 2>nul

:build
echo [QMS] Kreiram okruzenje i instaliram ovisnosti (jednom, ~1 min)...
py -3 -m venv .venv
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
echo GRESKA: Python nije pronadjen ("py" ne radi).
echo Instaliraj Python 3 s python.org i ukljuci "Add Python to PATH", pa pokreni run.bat ponovno.
echo.
pause
