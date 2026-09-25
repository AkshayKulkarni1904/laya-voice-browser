@echo off
setlocal
title LayaBrowse Windows Voice Browser

echo ======================================================================
echo  LayaBrowse for Windows - Local Voice Browser Assistant
echo ======================================================================
echo.

python -m laya_voice_browser_win start %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Running with Anaconda python fallback...
    "%USERPROFILE%\anaconda3\python.exe" -m laya_voice_browser_win start %*
)

pause
