@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "AYAR=%~dp0klasor.txt"
set "KLASOR="
if exist "%AYAR%" set /p KLASOR=<"%AYAR%"
if not defined KLASOR (
    echo Once baslat.bat dosyasini bir kez calistirip klasoru secin.
    pause
    exit /b 1
)
python -m pip install -q -r m0_schema\requirements.txt fastapi uvicorn qrcode
python -m hastagecmisi "%KLASOR%" --lan
pause
