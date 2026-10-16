@echo off
title EduMatch Public Tunnel
echo ========================================================
echo        EduMatch - Public Shareable Tunnel Launcher
echo ========================================================
echo.
echo Starting secure public Cloudflare Tunnel for port 5000...
echo.
cloudflared.exe tunnel --url http://localhost:5000
pause
