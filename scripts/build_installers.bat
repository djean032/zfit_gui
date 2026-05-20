@echo off
setlocal

set "ROOT_DIR=%~dp0.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"

set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%ISCC_PATH%" goto have_iscc

set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "%ISCC_PATH%" goto have_iscc

echo Could not find Inno Setup Compiler (ISCC.exe).
echo Install Inno Setup 6: https://jrsoftware.org/isdl.php
exit /b 1

:have_iscc
if not exist "%ROOT_DIR%\dist\ZScanStudio-Standard\ZScanStudio-Standard.exe" goto missing_standard
if not exist "%ROOT_DIR%\dist\ZScanStudio-Lab\ZScanStudio-Lab.exe" goto missing_lab

echo [1/2] Building Standard installer...
"%ISCC_PATH%" "%ROOT_DIR%\installer\ZScanStudio-Standard.iss"
if errorlevel 1 goto error

echo [2/2] Building Lab installer...
"%ISCC_PATH%" "%ROOT_DIR%\installer\ZScanStudio-Lab.iss"
if errorlevel 1 goto error

echo Installers created in %ROOT_DIR%\dist\installers
exit /b 0

:missing_standard
echo Missing Standard build output. Run scripts\build_pyinstaller_standard.bat first.
exit /b 1

:missing_lab
echo Missing Lab build output. Run scripts\build_pyinstaller_lab.bat first.
exit /b 1

:error
echo Installer build failed.
exit /b 1
