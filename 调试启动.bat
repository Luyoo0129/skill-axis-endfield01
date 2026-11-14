@echo off
setlocal
cd /d "%~dp0"

set "PY="

for %%D in (
    "%~dp0python\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "C:\Users\26413\.dsh\dsh-runtimes\dsh-next-primary-runtime\dependencies\python\python.exe"
) do if exist %%D if not defined PY set "PY=%%D"

if not defined PY (
    for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
)

if not defined PY (
    echo.
    echo Python not found.
    echo.
    pause
    exit /b 1
)

"%PY%" "%~dp0main.py"

echo.
echo ---- Program exited. If there was an error above, send me a screenshot. ----
pause >nul
