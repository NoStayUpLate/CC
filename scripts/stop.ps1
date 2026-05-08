# 停止 启动.bat 拉起的隐藏后端 + 前端进程。
# 优先用 logs/.pids.json 精确停；找不到就回落到杀 8000/5173 监听进程。

$ErrorActionPreference = 'SilentlyContinue'

$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root 'logs\.pids.json'

$stopped = @()

if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile -Raw | ConvertFrom-Json
    foreach ($name in 'backend','frontend') {
        $pidValue = $pids.$name
        if ($pidValue) {
            $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
                $stopped += "$name (PID $pidValue)"
            }
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# 回落：清理仍占用端口的进程（防止 PID 文件丢失或脏数据）
foreach ($p in 8000, 5173) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
            $stopped += "port $p -> $($proc.ProcessName) (PID $($c.OwningProcess))"
        }
    }
}

if ($stopped.Count -eq 0) {
    Write-Host "未发现运行中的服务"
} else {
    Write-Host "已停止：" -ForegroundColor Green
    $stopped | ForEach-Object { Write-Host "  - $_" }
}
