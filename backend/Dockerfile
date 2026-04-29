FROM python:3.11-slim

WORKDIR /app

# 安装 Playwright 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright Chromium 浏览器
RUN playwright install chromium

COPY . .

# 生产模式：去掉 --reload（避免容器内文件监听 + 多 worker 导致定时任务重复）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
