@echo off
chcp 65001 >nul
title 海外小说监测看板 - 停止器

cd /d %~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"
echo.
timeout /t 2 >nul
