@echo off
cd /d "%~dp0"
echo Open http://localhost:5000 on this computer.
echo For a phone on the same Wi-Fi, use this computer's LAN IP with port 5000.
python web_app.py
if errorlevel 1 pause
