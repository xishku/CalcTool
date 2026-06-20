@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo   HarmonyOS HelloWorld - Build Script
echo ============================================
echo.

if not exist "hvigorw.bat" (
    echo [ERROR] hvigorw.bat not found!
    echo Please open this project in DevEco Studio and wait for Sync to complete.
    pause
    exit /b 1
)

echo [1/2] Building HAP package...
call hvigorw.bat assembleHap --mode module -p product=default

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Build completed!
echo.
echo Output: entry\build\default\outputs\default\entry-default-signed.hap
echo.
echo Install: hdc install entry\build\default\outputs\default\entry-default-signed.hap
echo.
pause
