@echo off
setlocal

cd /d "%~dp0"

echo.
echo OpenCards
echo ==========
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=py -3"
  goto check_python
)

where python >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=python"
  goto check_python
)

echo Python 3 was not found on this computer.
echo.
echo Install Python from:
echo https://www.python.org/downloads/
echo.
echo During install, tick "Add python.exe to PATH" if Windows shows that option.
echo Then double-click this file again.
echo.
pause
exit /b 1

:check_python
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if not %errorlevel%==0 (
  echo OpenCards needs Python 3.11 or newer.
  echo.
  echo The Python found on this computer is:
  %PYTHON_CMD% --version
  echo.
  echo Install a newer Python from:
  echo https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

echo Starting OpenCards...
%PYTHON_CMD% "%~dp0app.py"
if not %errorlevel%==0 (
  echo.
  echo OpenCards stopped with an error.
  echo If this keeps happening, share the text in this window with the project maintainer.
  echo.
  pause
  exit /b %errorlevel%
)

exit /b 0
