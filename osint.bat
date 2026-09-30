@echo off
REM 
REM 

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%main.py"
set "VENV_DIR=%SCRIPT_DIR%venv"

REM 
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found. Please install Python 3.8+
    exit /b 1
)

REM 
if "%1"=="--help" goto :help
if "%1"=="-h" goto :help
if "%1"=="--install" goto :install
if "%1"=="" goto :interactive

REM 
if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" "%PYTHON_SCRIPT%" %*
) else (
    python "%PYTHON_SCRIPT%" %*
)
goto :end

:help
echo.
echo OSINT Toolkit - Windows Launcher
echo.
echo Usage:
echo   osint.bat                     Interactive mode
echo   osint.bat -t ^<target^>         Quick scan target
echo   osint.bat --install           Install dependencies
echo.
echo Quick Scan Examples:
echo   osint.bat -t user@email.com   Scan email
echo   osint.bat -t +79001234567     Scan phone
echo   osint.bat -t johndoe          Search username
echo   osint.bat -t example.com      Scan domain
echo.
echo Options:
echo   -t, --target ^<value^>    Target to scan
echo   --type ^<type^>           Force type: email^|phone^|username^|domain^|ip
echo   -o, --output ^<file^>     Save results to JSON
echo   --install               Install dependencies
echo   -h, --help              Show this help
echo.
goto :end

:install
echo Creating virtual environment...
python -m venv "%VENV_DIR%"
echo Installing dependencies...
"%VENV_DIR%\Scripts\pip.exe" install -r "%SCRIPT_DIR%requirements.txt"
echo.
echo Installation complete!
goto :end

:interactive
if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" "%PYTHON_SCRIPT%"
) else (
    python "%PYTHON_SCRIPT%"
)
goto :end

:end
endlocal
