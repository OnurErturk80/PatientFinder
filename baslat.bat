@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "AYAR=%~dp0klasor.txt"
set "KLASOR="
if exist "%AYAR%" set /p KLASOR=<"%AYAR%"
if defined KLASOR if not exist "%KLASOR%\" (
    echo Kayitli klasor bulunamadi: %KLASOR%
    set "KLASOR="
)
if not defined KLASOR (
    echo Access dosyalarinin klasorunu surukleyip birakin ve Enter'a basin.
    set /p KLASOR=Klasor: 
)
set "KLASOR=%KLASOR:"=%"
if not exist "%KLASOR%\" (
    echo Klasor bulunamadi. Pencereyi kapatip tekrar deneyin.
    pause
    exit /b 1
)
>"%AYAR%" echo %KLASOR%
python -m pip install -q -r m0_schema\requirements.txt fastapi uvicorn
echo Klasor: %KLASOR%
echo (Klasoru degistirmek icin klasor.txt dosyasini silin.)
python -m hastagecmisi "%KLASOR%"
pause
