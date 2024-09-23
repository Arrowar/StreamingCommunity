@echo off
:: BatchGotAdmin
::-------------------------------------
REM  --> Check for permissions
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

REM --> If error flag set, we do not have admin.
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params = %*:"="
    echo UAC.ShellExecute "cmd.exe", "/c %~s0 %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%CD%"
    CD /D "%~dp0"
::--------------------------------------
REM Check if running in PowerShell
@REM Check and install python
@REM where /q python >nul 2>nul
@REM if %errorlevel% neq 1 (
@REM     echo Checking Python...
@REM ) else (
@REM     call (exit /b 0)
@REM     echo python not found. Checking for Chocolatey...
@REM     REM Check if Chocolatey is installed
@REM     where /q choco >nul 2>nul
@REM     if %errorlevel% neq 1 (
@REM         echo Installing python using Chocolatey...
@REM         choco install python -y
@REM     ) else (
@REM         echo Chocolatey is not installed.
@REM         echo Please install Chocolatey first from https://chocolatey.org/install
@REM         echo After installing Chocolatey, you can run this script again to install ffmpeg.
@REM         echo Alternatively, you can install python manually from https://www.python.org/
@REM         exit /b 1
@REM     )
@REM )

REM Get the Python version
for /f "delims=" %%v in ('python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"') do set PYTHON_VERSION=%%v

REM Set the required version
set REQUIRED_VERSION=3.8

REM Compare the Python version with the required version
REM Split versions by dot and compare each segment
setlocal enabledelayedexpansion
for /f "tokens=1-3 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
    set PYTHON_PATCH=%%c
)

for /f "tokens=1-3 delims=." %%a in ("%REQUIRED_VERSION%") do (
    set REQUIRED_MAJOR=%%a
    set REQUIRED_MINOR=%%b
    set REQUIRED_PATCH=%%c
)

REM Compare major version
if !PYTHON_MAJOR! LSS !REQUIRED_MAJOR! (
    echo ERROR: Python version !PYTHON_VERSION! is < !REQUIRED_VERSION!. Exiting...
    exit /b 1
) else if !PYTHON_MAJOR! EQU !REQUIRED_MAJOR! (
    REM Compare minor version
    if !PYTHON_MINOR! LSS !REQUIRED_MINOR! (
        echo ERROR: Python version !PYTHON_VERSION! is < !REQUIRED_VERSION!. Exiting...
        exit /b 1
    ) else if !PYTHON_MINOR! EQU !REQUIRED_MINOR! (
        REM Compare patch version
        if !PYTHON_PATCH! LSS !REQUIRED_PATCH! (
            echo ERROR: Python version !PYTHON_VERSION! is < !REQUIRED_VERSION!. Exiting...
            exit /b 1
        )
    )
)

echo Python version %PYTHON_VERSION% is >= %REQUIRED_VERSION%. Continuing...

if exist ".venv\" (
    echo .venv exists. Installing requirements.txt.
    .venv\Scripts\python -m pip install -r requirements.txt
) else (
    echo Making .venv and installing requirements.txt...
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
)

where /q ffmpeg >nul 2>nul
if %errorlevel% neq 1 (
    echo ffmpeg exists.
) else (
    call (exit /b 0)
    echo ffmpeg not found. Checking for Chocolatey...
    REM Check if Chocolatey is installed
    where /q choco >nul 2>nul
    if %errorlevel% neq 1 (
        echo Installing ffmpeg using Chocolatey...
        choco install ffmpeg -y
    ) else (
        echo Chocolatey is not installed.
        echo Please install Chocolatey first from https://chocolatey.org/install
        echo After installing Chocolatey, you can run this script again to install ffmpeg.
        echo Alternatively, you can install ffmpeg manually from https://www.ffmpeg.org/
        exit /b 1
    )
)


REM Check if OpenSSL exists
where /q openssl >nul 2>nul
if %errorlevel% neq 1 (
    echo openssl exists.
    goto end
)
call (exit /b 0)

REM Check if pycryptodome is installed
.venv\Scripts\pip list | findstr /i "pycryptodome" >nul
if %errorlevel% equ 0 (
    echo pycryptodome exists.
    goto end
)
call (exit /b 0)

REM Prompt for installation option
echo Please choose an option:
echo 1) openssl
echo 2) pycryptodome
set /p choice="Enter your choice (1): "

REM Handle the choice
if "%choice%"=="2" (
    echo Installing pycryptodome.
    .venv\Scripts\pip install pycryptodome
) else (
    echo Installing openssl.
    echo Checking for Chocolatey...

    REM Check if Chocolatey is installed
    where /q choco >nul 2>nul
    if %errorlevel% neq 1 (
        echo Installing openssl using Chocolatey...
        choco install openssl -y
    ) else (
        echo Chocolatey is not installed.
        echo Please install Chocolatey first from https://chocolatey.org/install
        echo After installing Chocolatey, you can run this script again to install openssl.
        echo Alternatively, you can install OpenSSH manually from https://www.openssl.com/.
        exit /b 1
    )
)

:end

setlocal enabledelayedexpansion & set "tempfile=%temp%\tempfile.txt" & (echo #^^!.venv\Scripts\python & type run.py | more +1) > "!tempfile!" & move /Y "!tempfile!" run.py >nul 2>nul

echo Everything is installed^^!
echo Run StreamingCommunity with '.\run.py'
pause
