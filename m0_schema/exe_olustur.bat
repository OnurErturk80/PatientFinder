@echo off
REM Windows'ta bir kez çalıştırın: HastaGecmisi_SemaKesfi.exe üretir (dist klasörü).
chcp 65001 >nul
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller || goto :hata
python -m PyInstaller --onefile --console --name HastaGecmisi_SemaKesfi --paths . run_m0.py || goto :hata
echo.
echo Tamam: dist\HastaGecmisi_SemaKesfi.exe
pause
exit /b 0
:hata
echo Bir hata olustu.
pause
