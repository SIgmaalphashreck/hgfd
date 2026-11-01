@echo off
setlocal
cd /d "%~dp0"
title SquallowTweaks
where py >nul 2>nul
if errorlevel 1 (
  echo Python (py.exe) wurde nicht gefunden. Installiere Python 3.10+ von https://www.python.org/downloads/
  pause
  exit /b 1
)
py -3 -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 ( echo Installation fehlgeschlagen. & pause & exit /b 1 )
py -3 main.py
if errorlevel 1 ( echo SquallowTweaks wurde mit einem Fehler beendet. Log: %%LOCALAPPDATA%%\SquallowTweaks\squallow.log & pause )
endlocal
