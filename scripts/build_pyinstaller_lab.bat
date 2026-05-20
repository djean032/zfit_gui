@echo off
setlocal

set "ROOT_DIR=%~dp0.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"

echo [1/3] Syncing dependencies with hardware extra...
call uv sync --extra hardware
if errorlevel 1 goto :error

echo [2/3] Building Lab onedir executable...
call uv run pyinstaller --noconfirm --clean --onedir --windowed --name ZScanStudio-Lab --paths src --hidden-import nidaqmx app.py
if errorlevel 1 goto :error

echo [3/3] Lab build complete.
echo Output: %ROOT_DIR%\dist\ZScanStudio-Lab\ZScanStudio-Lab.exe
exit /b 0

:error
echo Build failed.
exit /b 1
