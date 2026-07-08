@echo off
setlocal
cd /d "%~dp0"
rem Jjanggu standalone exe build (result: dist\Jjanggu\Jjanggu.exe)

python -m pip install pyinstaller || (pause & exit /b 1)
python -m PyInstaller --noconfirm --noconsole --name Jjanggu ^
    --add-data "assets;assets" main.py
if errorlevel 1 (pause & exit /b 1)

echo.
echo Done: dist\Jjanggu\Jjanggu.exe
pause
