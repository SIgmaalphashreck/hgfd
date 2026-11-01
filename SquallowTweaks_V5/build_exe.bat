@echo off
setlocal
cd /d "%~dp0"
title Build SquallowTweaks EXE
py -3 -m pip install --disable-pip-version-check -r requirements.txt pyinstaller
if errorlevel 1 goto error
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin --name SquallowTweaks --icon assets/squallow.ico --add-data "assets;assets" --collect-all customtkinter --collect-submodules pages main.py
if errorlevel 1 goto error
echo Fertig: dist\SquallowTweaks.exe  (PresentMon.exe fuer Messungen daneben legen oder per Release-Build mitliefern)
pause
exit /b 0
:error
echo Build fehlgeschlagen.
pause
exit /b 1
