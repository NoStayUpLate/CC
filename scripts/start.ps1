# 隐藏启动后端 + 前端，写日志到 logs/，记录 PID 到 logs/.pids.json，最后打开浏览器。
# 由 启动.bat 调用；也可手动运行 powershell -ExecutionPolicy Bypass -File scripts\start.ps1

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

# 让 Python 不缓冲 stdout，日志能实时写出来
$env:PYTHONUNBUFFERED = '1'

# ── 后端：python -m uvicorn ────────────────────────────────────
Write-Host "启动后端 (隐藏窗口)..."
$backend = Start-Process -FilePath 'python' `
    -ArgumentList @('-m','uvicorn','main:app','--host','0.0.0.0','--port','8000') `
    -WorkingDirectory (Join-Path $root 'backend') `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'backend.log') `
    -RedirectStandardError  (Join-Path $logs 'backend.err.log') `
    -PassThru

# ── 前端：npm run dev ─────────────────────────────────────────
# 直接启 node + vite 而不是 npm，是为了避免 npm 包装层 spawn 的 node 子进程
# 在 -RedirectStandardOutput 模式下日志被吞 + 关进程时孤儿。
$vite = Join-Path $root 'frontend\node_modules\vite\bin\vite.js'
if (-not (Test-Path $vite)) {
    Write-Host "ERROR: vite 未找到 ($vite)。请先在 frontend/ 下执行 npm install。" -ForegroundColor Red
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "启动前端 (隐藏窗口)..."
$frontend = Start-Process -FilePath 'node' `
    -ArgumentList @($vite,'--host','0.0.0.0','--port','5173') `
    -WorkingDirectory (Join-Path $root 'frontend') `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'frontend.log') `
    -RedirectStandardError  (Join-Path $logs 'frontend.err.log') `
    -PassThru

# ── 记录 PID，停止脚本用 ─────────────────────────────────────
@{
    backend  = $backend.Id
    frontend = $frontend.Id
    started  = (Get-Date).ToString('s')
} | ConvertTo-Json | Set-Content -Path (Join-Path $logs '.pids.json') -Encoding utf8

# ── 等前端 :5173 就绪 (最多 60 秒) ───────────────────────────
Write-Host "等待前端 5173 端口就绪..."
$deadline = (Get-Date).AddSeconds(60)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $c = New-Object Net.Sockets.TcpClient('127.0.0.1', 5173)
        $c.Close()
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $ready) {
    Write-Host "前端 60 秒内未就绪，请查看 logs\frontend.log" -ForegroundColor Yellow
    exit 2
}

# ── 打开浏览器 ───────────────────────────────────────────────
Start-Process 'http://localhost:5173'
Write-Host "✅ 已启动" -ForegroundColor Green
Write-Host "   前端: http://localhost:5173"
Write-Host "   后端: http://localhost:8000"
Write-Host "   日志: $logs"
