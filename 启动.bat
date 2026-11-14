@echo off
setlocal
cd /d "%~dp0"

rem ---- locate a pythonw.exe ----
set "PYW="

for %%D in (
    "%~dp0python\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    "C:\Users\26413\.dsh\dsh-runtimes\dsh-next-primary-runtime\dependencies\python\pythonw.exe"
) do if exist %%D if not defined PYW set "PYW=%%D"

if not defined PYW (
    for /f "delims=" %%P in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%P"
)

if defined PYW (
    start "" "%PYW%" "%~dp0main.py"
    exit /b 0
)

echo.
echo Python not found.
echo Please install Python 3.10 or newer, and check "Add Python to PATH" during setup.
echo.
pause
