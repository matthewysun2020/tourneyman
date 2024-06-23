@echo off

:: Check if Node.js is installed
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js not found. Installing...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-ExecutionPolicy Bypass -Scope Process; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"
    choco install nodejs
) else (
    echo Node.js is already installed.
)

:: Check if Localtunnel is installed
where lt >nul 2>nul
if %errorlevel% neq 0 (
    echo Localtunnel not found. Installing...
    npm install -g localtunnel
) else (
    echo Localtunnel is already installed.
)
