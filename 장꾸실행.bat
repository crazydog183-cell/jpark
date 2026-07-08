@echo off
setlocal
cd /d "%~dp0"

rem ── Python 확인 ─────────────────────────────────────────────
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [Jjanggu] Python not found. Install it from https://www.python.org/downloads/
        echo           ^(check "Add python.exe to PATH" during install^)
        pause
        exit /b 1
    )
    set "PY=python"
)

rem ── 최초 1회 의존성 설치 ────────────────────────────────────
if not exist ".deps_ok" (
    echo [Jjanggu] Installing dependencies... ^(first run only^)
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [Jjanggu] pip install failed.
        pause
        exit /b 1
    )
    echo ok> .deps_ok
)

rem ── 콘솔 창 없이 실행 (pythonw 우선) ────────────────────────
where %PY%w >nul 2>nul
if %errorlevel%==0 (
    start "Jjanggu" %PY%w main.py
) else (
    start "Jjanggu" %PY% main.py
)
exit /b 0
