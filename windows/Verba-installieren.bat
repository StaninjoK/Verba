@echo off
REM Doppelklick: startet die Installation von Verba (PowerShell-Skript daneben).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-verba.ps1"
if errorlevel 1 (
  echo.
  echo Installation abgebrochen. Bitte die Meldung oben kopieren und an Claude schicken.
  pause
)
