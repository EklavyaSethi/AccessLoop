@echo off
rem AccessLoop setup for Windows. Runs setup_windows.ps1 without changing the system-wide PowerShell execution policy.
rem Usage:  setup_windows.cmd   [-AI] [-Quick]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1" %*
exit /b %ERRORLEVEL%
