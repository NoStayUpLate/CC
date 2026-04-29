FROM python:3.11-slim

WORKDIR /app

# ── 国内构建加速：Debian / PyPI / Playwright 全部走国内镜像 ──
# 兼容 trixie (deb822 格式 /etc/apt/sources.list.d/debian.sources)
# 与 bookworm 之前的 /etc/apt/sources.list 两种格式
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
        sed -i 's|http://security.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    fi && \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list && \
        sed -i 's|http://security.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list; \
    fi

# 安装 Playwright 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# pip 走阿里云源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright Chromium 走 npmmirror 镜像（官方 azureedge 在国内极慢）
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
RUN playwright install chromium

COPY . .

# 生产模式：去掉 --reload（避免容器内文件监听 + 多 worker 导致定时任务重复）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
