@echo off
:: build.bat - One-click build script for YT Downloader
:: Run from the project root with your venv active:
::   .\build.bat

echo ============================================
echo  YT Downloader - Build Script
echo ============================================
echo.

:: Store project root
set ROOT=%~dp0
cd /d "%ROOT%"

:: Check PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Clean previous build
echo [1/3] Cleaning previous build...
if exist dist\YTDownloader rmdir /s /q dist\YTDownloader
if exist build rmdir /s /q build

:: Run PyInstaller
echo [2/3] Building executable with PyInstaller...
pyinstaller youtube_downloader.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo [3/3] PyInstaller build complete.
echo   Executable: dist\YTDownloader\YTDownloader.exe
echo.

:: Create installer output dir
if not exist installer\Output mkdir installer\Output

:: Find Inno Setup
set INNO=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set INNO="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set INNO="C:\Program Files\Inno Setup 6\ISCC.exe"

if "%INNO%"=="" (
    echo NOTE: Inno Setup not found - skipping installer.
    echo Download from: https://jrsoftware.org/isinfo.php
    goto :done
)

echo [4/3] Building installer with Inno Setup...
%INNO% "%ROOT%installer\setup.iss"
if errorlevel 1 (
    echo ERROR: Inno Setup build failed.
    pause
    exit /b 1
)

echo.
echo Installer: installer\Output\YTDownloader_Setup.exe

:done
echo.
echo ============================================
echo  Build complete!
echo ============================================
pause