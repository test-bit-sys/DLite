@echo off
REM ─── DLite installer build script ─────────────────────────────
REM Runs from the repo root:  installer\build_installer.bat
REM Produces dist\DLite-Setup.exe

setlocal
cd /d %~dp0\..

echo ===================================
echo  DLite — Installer Build Script
echo ===================================
echo.

REM ── 1. Install build deps ──
echo [1/4] Installing build dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ERROR: failed to install PyInstaller.
    exit /b 1
)

REM ── 2. Build the onedir bundle ──
echo.
echo [2/4] Building application bundle with PyInstaller...
if exist build\DLite rmdir /s /q build\DLite
if exist dist\DLite rmdir /s /q dist\DLite
python -m PyInstaller installer\DLite.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

REM ── 3. Locate Inno Setup compiler ──
echo.
echo [3/4] Locating Inno Setup (ISCC)...
set "ISCC="
for %%P in (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
) do (
    if exist %%P set "ISCC=%%~P"
)
if "%ISCC%"=="" (
    where iscc >nul 2>&1 && for /f "delims=" %%I in ('where iscc') do set "ISCC=%%I"
)
if "%ISCC%"=="" (
    echo ERROR: Inno Setup (ISCC.exe) not found.
    echo        Install it from https://jrsoftware.org/isdl.php
    exit /b 1
)

REM ── 4. Compile installer ──
echo.
echo [4/4] Compiling installer with Inno Setup...
"%ISCC%" installer\DLite-Setup.iss
if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed.
    exit /b 1
)

echo.
echo ===================================
echo  Done! Installer: dist\DLite-Setup.exe
echo ===================================
endlocal