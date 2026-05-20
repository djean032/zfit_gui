@echo off
setlocal

set "ROOT_DIR=%~dp0.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"

echo [1/3] Syncing core dependencies...
call uv sync
if errorlevel 1 goto :error

echo [2/3] Building Standard onedir executable...
call uv run pyinstaller --noconfirm --clean --onedir --windowed --name ZScanStudio-Standard --paths src --exclude-module nidaqmx app.py
if errorlevel 1 goto :error

echo [3/3] Standard build complete.
echo Output: %ROOT_DIR%\dist\ZScanStudio-Standard\ZScanStudio-Standard.exe
exit /b 0

:error
echo Build failed.
exit /b 1
