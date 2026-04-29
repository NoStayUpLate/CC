@echo off
chcp 65001 >nul
title 海外小说监测看板

echo 正在启动后端...
start "后端 API" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo 正在启动前端...
start "前端页面" cmd /k "cd /d %~dp0frontend && (if not exist node_modules call npm install) && call npm run dev"

echo 等待前端 5173 端口就绪...
:waitloop
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "try { (New-Object Net.Sockets.TcpClient(""127.0.0.1"",5173)).Close(); exit 0 } catch { exit 1 }"
if errorlevel 1 goto waitloop

echo 正在打开浏览器...
start http://localhost:5173

echo.
echo 已启动完成！
echo   后端 API : http://localhost:8000
echo   前端页面 : http://localhost:5173
echo   API 文档 : http://localhost:8000/docs
echo.
echo 关闭此窗口不会停止服务，请直接关闭"后端 API"和"前端页面"两个窗口。
pause
