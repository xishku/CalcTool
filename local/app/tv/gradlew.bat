@echo off
setlocal

set DIRNAME=%~dp0

:: Change to project directory
cd /d "%DIRNAME%"

:: Auto-detect JAVA_HOME
if not defined JAVA_HOME (
    if exist "C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot\bin\java.exe" (
        set JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot
    )
)
if not defined JAVA_HOME (
    for /d %%i in ("C:\Program Files\Microsoft\jdk-17*") do (
        if exist "%%i\bin\java.exe" set JAVA_HOME=%%i
    )
)

if not defined JAVA_HOME (
    echo ERROR: JAVA_HOME is not set. Please install JDK 17+.
    echo Try: winget install Microsoft.OpenJDK.17
    exit /b 1
)

echo JAVA_HOME=%JAVA_HOME%

set GRADLE_HOME=%DIRNAME%.gradle-local
if not exist "%GRADLE_HOME%\bin\gradle.bat" (
    echo ERROR: Gradle distribution not found at %GRADLE_HOME%
    exit /b 1
)

:: Run Gradle
call "%GRADLE_HOME%\bin\gradle.bat" %*
exit /b %ERRORLEVEL%
