@rem Gradle 8.7 launcher. Official wrapper bootstrap is verified before first use.
@echo off
setlocal
set "APP_HOME=%~dp0"
if defined JAVA_HOME goto findJavaFromJavaHome
set "JAVA_EXE=java.exe"
%JAVA_EXE% -version >NUL 2>&1
if "%ERRORLEVEL%" == "0" goto execute
echo ERROR: JDK 17 is required. Set JAVA_HOME to your JDK 17 installation. 1>&2
exit /b 1

:findJavaFromJavaHome
set "JAVA_EXE=%JAVA_HOME%\bin\java.exe"
if exist "%JAVA_EXE%" goto execute
echo ERROR: JAVA_HOME does not point to a JDK installation. 1>&2
exit /b 1

:execute
if exist "%APP_HOME%gradle\wrapper\gradle-wrapper.jar" goto launch
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%APP_HOME%tools\Install-GradleWrapper.ps1"
if not "%ERRORLEVEL%" == "0" exit /b 1
:launch
"%JAVA_EXE%" %JAVA_OPTS% %GRADLE_OPTS% -classpath "%APP_HOME%gradle\wrapper\gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain %*
exit /b %ERRORLEVEL%
