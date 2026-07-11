@echo off
setlocal
cd /d "%~dp0"
rem Jjanggu standalone exe build (result: dist\Jjanggu.exe)

python -m pip install pyinstaller || (pause & exit /b 1)
python -m PyInstaller --noconfirm --onefile --noconsole --name Jjanggu ^
    --add-data "assets;assets" --hidden-import comtypes.stream main.py
if errorlevel 1 (pause & exit /b 1)

echo.
echo Done: dist\Jjanggu.exe
pause
