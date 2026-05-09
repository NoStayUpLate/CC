FROM python:3.11-slim

WORKDIR /app

# 是否安装 Chromium 浏览器二进制 + 系统依赖。
# - true（开发 / 海外节点）：装 Chromium 和 libnss/libgtk 等 ~300MB 系统库，可跑爬虫
# - false（默认，生产 1C2G）：只装 playwright python 包，scrapers 仍能 import 但跑 scrape() 会失败
#                              省 ~700MB 镜像 + 构建时不再 OOM
# build 命令：docker build --build-arg INSTALL_PLAYWRIGHT_CHROMIUM=true ./backend
ARG INSTALL_PLAYWRIGHT_CHROMIUM=false

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

# Playwright Chromium 系统依赖（libnss/libgtk/...），仅 INSTALL_PLAYWRIGHT_CHROMIUM=true 时安装
RUN if [ "$INSTALL_PLAYWRIGHT_CHROMIUM" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            wget curl gnupg \
            libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
            libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
            libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 \
            && rm -rf /var/lib/apt/lists/*; \
    fi

# pip 走阿里云源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

COPY requirements.txt .
# playwright 的 python 包很小（~10MB），始终装上让 from playwright import ... 不报 ImportError；
# 真正占空间的是 Chromium 二进制（~200MB）+ 系统依赖，留给下面按需安装
RUN pip install --no-cache-dir -r requirements.txt

# Playwright Chromium 走 npmmirror 镜像（官方 azureedge 在国内极慢）
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
RUN if [ "$INSTALL_PLAYWRIGHT_CHROMIUM" = "true" ]; then \
        playwright install chromium; \
    fi

COPY . .

# 生产模式：去掉 --reload（避免容器内文件监听 + 多 worker 导致定时任务重复）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
