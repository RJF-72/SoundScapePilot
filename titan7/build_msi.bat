@echo off
setlocal

REM Build directory
set BUILD_DIR=build_msi
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

REM Locate WiX Toolset
set WIX_BIN=
if exist "C:\Program Files (x86)\WiX Toolset v3.14\bin\candle.exe" set WIX_BIN=C:\Program Files (x86)\WiX Toolset v3.14\bin
if exist "C:\Program Files\WiX Toolset v3.14\bin\candle.exe" set WIX_BIN=C:\Program Files\WiX Toolset v3.14\bin
if exist "C:\Program Files (x86)\WiX Toolset\v3.14\bin\candle.exe" set WIX_BIN=C:\Program Files (x86)\WiX Toolset\v3.14\bin
if exist "C:\Program Files\WiX Toolset\v3.14\bin\candle.exe" set WIX_BIN=C:\Program Files\WiX Toolset\v3.14\bin

if "%WIX_BIN%"=="" (
    echo ERROR: WiX Toolset not found (candle.exe not located).
    echo Install WiX Toolset (administrator required), then re-run this script.
    echo   winget install WiXToolset.WiXToolset
    goto end
)

echo Using WiX: %WIX_BIN%

REM Step 1: Compile .wxs to .wixobj
echo Compiling WiX source...
"%WIX_BIN%\candle.exe" titan7_installer.wxs -o "%BUILD_DIR%\titan7_installer.wixobj"
if errorlevel 1 goto error

REM Step 2: Link .wixobj to .msi
echo Linking MSI...
"%WIX_BIN%\light.exe" "%BUILD_DIR%\titan7_installer.wixobj" -o "SoundScape_Pilot_Setup.msi" -ext WixUIExtension -sice:ICE80
if errorlevel 1 goto error

echo.
echo Build complete: SoundScape_Pilot_Setup.msi
goto end

:error
echo.
echo BUILD FAILED
exit /b 1

:end
endlocal
