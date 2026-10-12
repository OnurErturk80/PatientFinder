@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m pip install -q -r m0_schema\requirements.txt fastapi uvicorn
set /p KLASOR=Access dosyalarinin klasoru (surukleyip birakin): 
python -m hastagecmisi %KLASOR%
pause
