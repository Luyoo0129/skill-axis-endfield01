@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "GIT=%~dp0.gittools\mingit\cmd\git.exe"

if not exist "%GIT%" (
    echo.
    echo Git not found at: %GIT%
    echo Install Git from https://git-scm.com/download/win and use "git" directly instead.
    echo.
    pause
    exit /b 1
)

"%GIT%" remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo.
    echo No remote configured yet.
    echo Create a repo at https://github.com/new  ^(choose Private^)
    echo Then paste the repo URL below. It looks like:
    echo    https://github.com/YOUR_NAME/skill-axis-endfield.git
    echo.
    set /p "URL=Repo URL: "
    if "!URL!"=="" (
        echo Cancelled.
        pause
        exit /b 1
    )
    "%GIT%" remote add origin "!URL!"
    echo Remote added: !URL!
)

echo.
echo Pushing to GitHub ...
echo A browser window may open for you to sign in to GitHub.
echo.
"%GIT%" push -u origin main

echo.
echo ---- Done ----
echo If push failed with authentication error, use a Personal Access Token
echo instead of your password: GitHub - Settings - Developer settings -
echo Personal access tokens - Tokens ^(classic^) - generate with "repo" scope.
echo.
pause
