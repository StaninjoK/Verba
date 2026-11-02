@echo off
title Verba
cd /d "%~dp0.."
echo Verba startet ... der Browser oeffnet sich gleich. Dieses Fenster offen lassen.
node scripts\dev.mjs --prod --open
pause
