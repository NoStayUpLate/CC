@echo off
chcp 65001 >nul
title 海外小说监测看板 - 启动器

cd /d %~dp0

REM 端口占用：先释放 8000 / 5173，避免重复启动堆叠
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1" >nul 2>&1

REM 前端首次启动需要 npm install（这一步保留可见，让用户看到下载进度）
if not exist "%~dp0frontend\node_modules" (
    echo 首次启动需要 npm install，预计 1-3 分钟，请稍候...
    pushd "%~dp0frontend"
    call npm install
    popd
    if errorlevel 1 (
        echo.
        echo ❌ npm install 失败，请检查网络或 frontend 目录。
        pause
        exit /b 1
    )
)

REM 调 PowerShell 隐藏启动后端 + 前端
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
set RC=%errorlevel%

if %RC% neq 0 (
    echo.
    echo ❌ 启动失败 ^(exit %RC%^)，请查看 logs\backend.log / frontend.log
    pause
    exit /b %RC%
)

echo.
echo ✅ 启动完成（无 cmd 窗口运行）
echo    前端: http://localhost:5173
echo    后端: http://localhost:8000
echo    日志: %~dp0logs\
echo    停止服务请双击 停止.bat
echo.
timeout /t 3 >nul
