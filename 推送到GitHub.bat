@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "MG=%~dp0.gittools\mingit"
set "GIT=%MG%\cmd\git.exe"
set "PATH=%MG%\ucrt64\bin;%MG%\cmd;%PATH%"

if not exist "%GIT%" goto nogit

echo.
echo ============================================
echo  Push skill-axis-endfield to GitHub
echo ============================================
echo.

"%GIT%" config --local credential.helper manager >nul 2>&1

"%GIT%" remote get-url origin >nul 2>&1
if errorlevel 1 goto seturl
goto push

:seturl
echo No remote configured yet.
echo Example URL:
echo    https://github.com/YOUR_NAME/skill-axis-endfield.git
echo.
set /p "URL=Repo URL: "
if "!URL!"=="" goto cancel
"%GIT%" remote add origin "!URL!"
echo Remote added.
echo.

:push
echo Remote:
"%GIT%" remote get-url origin
echo.
echo A "Connect to GitHub" window will open.
echo Sign in with your browser, then come back here.
echo.
"%GIT%" push -u origin main
if errorlevel 1 goto failed

echo.
echo --------------------------------------------
echo  Push OK
echo --------------------------------------------
echo Next step: add your friend as collaborator
echo   Repo page - Settings - Collaborators - Add people
echo.
goto end

:failed
echo.
echo --------------------------------------------
echo  Push FAILED
echo --------------------------------------------
echo If the message mentions authentication or
echo "could not read Username", use a Personal Access Token as the password:
echo   GitHub - Settings - Developer settings -
echo   Personal access tokens - Tokens (classic) -
echo   Generate new token - check "repo" scope
echo.
echo Or ask the assistant to push using a token.
echo.

:end
echo.
pause
exit /b 0

:nogit
echo Portable Git not found:
echo    %GIT%
echo Install Git from https://git-scm.com/download/win instead.
echo.
pause
exit /b 1

:cancel
echo Cancelled.
echo.
pause
exit /b 1
