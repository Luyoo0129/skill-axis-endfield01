@echo off
setlocal

cd /d "%~dp0"

set "MG=%~dp0.gittools\mingit"
set "GIT=%MG%\cmd\git.exe"

if not exist "%GIT%" (
    echo.
    echo Portable Git not found: %GIT%
    echo Install Git from https://git-scm.com/download/win and run: git push -u origin main
    echo.
    pause
    exit /b 1
)

rem GCM lives in ucrt64\bin - must be on PATH so "manager" resolves
set "PATH=%MG%\ucrt64\bin;%MG%\cmd;%PATH%"

rem make sure the credential helper is usable
"%GIT%" config --local credential.helper manager >nul 2>&1

echo.
echo ============================================
echo  Push skill-axis-endfield to GitHub
echo ============================================
echo.

"%GIT%" remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo No remote configured.
    echo Example: https://github.com/YOUR_NAME/skill-axis-endfield.git
    echo.
    set /p "URL=Repo URL: "
    if "!URL!"=="" (
        echo Cancelled.
        pause
        exit /b 1
    )
    "%GIT%" remote add origin "!URL!"
)

echo Remote: 
"%GIT%" remote get-url origin
echo.
echo A "Connect to GitHub" window will open. Sign in there.
echo.
"%GIT%" push -u origin main

echo.
echo ---- Result ----
if errorlevel 1 (
    echo Push FAILED. See messages above.
    echo.
    echo If it says authentication / could not read Username:
    echo   use a Personal Access Token as the password.
    echo   GitHub - Settings - Developer settings - Personal access tokens
    echo   - Tokens ^(classic^) - Generate new token - check "repo" scope
    echo.
    echo Or ask the assistant to push with a token instead.
) else (
    echo Push OK. Open your repo page and add your friend as collaborator:
    echo   Settings - Collaborators - Add people
)
echo.
pause
