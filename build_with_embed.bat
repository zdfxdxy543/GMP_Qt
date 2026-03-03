@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "ROOT=%CD%"
set "EMBED_PY=%ROOT%\python-embed\python.exe"
set "EMBED_DIR=%ROOT%\python-embed"
set "VIRTUALENV_PYZ=%ROOT%\virtualenv.pyz"
set "VENV_DIR=%ROOT%\.venv_embed"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "SPECS_DIR=%ROOT%\build\specs"

if not exist "%EMBED_PY%" (
    echo [ERROR] python-embed\python.exe not found.
    exit /b 1
)

if not exist "%VIRTUALENV_PYZ%" (
    echo [ERROR] virtualenv.pyz not found.
    exit /b 1
)

if not exist "%ROOT%\cascading_wizard.py" (
    echo [ERROR] cascading_wizard.py not found in project root.
    exit /b 1
)

if not exist "%SPECS_DIR%" mkdir "%SPECS_DIR%"

echo [0/5] Checking embedded Python extension modules...
"%EMBED_PY%" -c "import _socket" >nul 2>nul
if errorlevel 1 (
    echo [WARN] _socket is missing in python-embed, trying to bootstrap *.pyd from local CPython...

    set "CPY_PREFIX="
    for /f "usebackq delims=" %%I in (`py -3 -c "import sys; print(sys.base_prefix)" 2^>nul`) do set "CPY_PREFIX=%%I"

    if not defined CPY_PREFIX if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "CPY_PREFIX=%LocalAppData%\Programs\Python\Python313"
    if not defined CPY_PREFIX if exist "%ProgramFiles%\Python313\python.exe" set "CPY_PREFIX=%ProgramFiles%\Python313"

    if defined CPY_PREFIX (
        if exist "!CPY_PREFIX!\DLLs\*.pyd" (
            echo [INFO] Copying extension modules from: !CPY_PREFIX!\DLLs
            copy /y "!CPY_PREFIX!\DLLs\*.pyd" "%EMBED_DIR%\" >nul
        )
    )

    "%EMBED_PY%" -c "import _socket" >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] _socket is still missing in python-embed.
        echo [ERROR] Please install Python 3.x on this machine so script can copy *.pyd from its DLLs folder.
        exit /b 1
    )
)

echo [1/5] Creating virtual environment with python-embed + virtualenv.pyz...
"%EMBED_PY%" "%VIRTUALENV_PYZ%" "%VENV_DIR%"
if errorlevel 1 goto :error

if not exist "%VENV_PY%" (
    echo [ERROR] Virtual environment python not found: %VENV_PY%
    exit /b 1
)

echo [2/5] Installing dependencies...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :error

if exist "%ROOT%\requirements.txt" (
    "%VENV_PY%" -m pip install -r "%ROOT%\requirements.txt"
    if errorlevel 1 goto :error
) else (
    echo [WARN] requirements.txt not found, skipping.
)

"%VENV_PY%" -m pip install pyinstaller
if errorlevel 1 goto :error

echo [3/5] Building root script: cascading_wizard.py...
if exist "%SPECS_DIR%\cascading_wizard.spec" del /f /q "%SPECS_DIR%\cascading_wizard.spec"

if exist "%ROOT%\main.ico" (
    "%VENV_PY%" -m PyInstaller --noconfirm --onefile --icon "%ROOT%\main.ico" --distpath "%ROOT%" --workpath "%ROOT%\build\pyinstaller\root" --specpath "%SPECS_DIR%" "%ROOT%\cascading_wizard.py"
) else (
    echo [WARN] main.ico not found in project root, building without icon.
    "%VENV_PY%" -m PyInstaller --noconfirm --onefile --distpath "%ROOT%" --workpath "%ROOT%\build\pyinstaller\root" --specpath "%SPECS_DIR%" "%ROOT%\cascading_wizard.py"
)
if errorlevel 1 goto :error

echo [4/5] Building all Python files under src\ into tools\ with same relative paths...
for /r "%ROOT%\src" %%F in (*.py) do (
    set "FULL_FILE=%%~fF"
    set "REL_FILE=!FULL_FILE:%ROOT%\src\=!"

    set "FULL_DIR=%%~dpF"
    set "REL_DIR=!FULL_DIR:%ROOT%\src\=!"
    if "!REL_DIR:~-1!"=="\" set "REL_DIR=!REL_DIR:~0,-1!"

    set "OUT_DIR=%ROOT%\tools\!REL_DIR!"
    if not exist "!OUT_DIR!" mkdir "!OUT_DIR!"

    set "BUILD_TAG=!REL_DIR!_%%~nF"
    set "BUILD_TAG=!BUILD_TAG:\=_!"
    set "BUILD_TAG=!BUILD_TAG:/=_!"

    echo    - %%~fF
    "%VENV_PY%" -m PyInstaller --noconfirm --onefile --name "%%~nF" --distpath "!OUT_DIR!" --workpath "%ROOT%\build\pyinstaller\!BUILD_TAG!" --specpath "%SPECS_DIR%" "%%~fF"
    if errorlevel 1 goto :error
)

echo [5/5] Done.
echo Output:
echo   - Root EXE: %ROOT%
echo   - Src EXEs: %ROOT%\tools\(same relative path as src)
exit /b 0

:error
echo [ERROR] Build failed.
exit /b 1
