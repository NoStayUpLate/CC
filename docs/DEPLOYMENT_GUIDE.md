# 上云部署完整教程（阿里云 ECS / 1C2G 即可）

> 本教程基于实际部署经历整理，给团队同事按图施工用。**第一次部署预计 30-60 分钟**（瘦身后比早期版本快得多，不再装 ClickHouse / Chromium）。
> 部署目标：把项目从 GitHub 克隆到云服务器，跑起 docker compose 栈（2 个容器），浏览器能访问。
>
> 适用范围：本项目（FastAPI + React + DuckDB 嵌入式），但**部署流程的前 5 章对任何 docker compose 项目通用**。

---

## 目录

- [0. 准备工作清单](#0-准备工作清单)
- [1. MobaXterm 使用速成](#1-mobaxterm-使用速成)
- [2. 阿里云 ECS 安全组配置](#2-阿里云-ecs-安全组配置)
- [3. 装 Docker（绕开 GFW）](#3-装-docker绕开-gfw)
- [4. 拉项目代码](#4-拉项目代码)
- [5. 配置 .env.production](#5-配置-envproduction)
- [6. 一键启动](#6-一键启动)
- [7. 浏览器访问 + 注册第一个账号](#7-浏览器访问--注册第一个账号)
- [8. 上传本地数据到 DuckDB（可选）](#8-上传本地数据到-duckdb可选)
- [9. 常见踩坑 FAQ（基于真实经历）](#9-常见踩坑-faq基于真实经历)
- [10. 日常运维命令速查](#10-日常运维命令速查)
- [11. 后续可选：买域名 + HTTPS](#11-后续可选买域名--https)

---

## 0. 准备工作清单

开始前确保你有：

- [ ] **阿里云 ECS 实例**（**最低 1 核 2G、40G 系统盘即可**；瘦身后内存占用 ~250MB；推荐 Ubuntu 22.04+ 或 Anolis 8）
- [ ] **ECS 的公网 IP** + **登录密码（或 SSH key）**
- [ ] **本地装好 MobaXterm**（Windows 用户，下载：<https://mobaxterm.mobatek.net/download.html>，免费版够用）
- [ ] **GitHub 仓库地址**（自己创建，利用国内的 gitee 也可以），如果是私有仓库还需要 PAT

> ⚠️ **国内 ECS 警告**：因为技术部署的服务器是杭州的，无法在线上运行爬虫代码。建议不要尝试服务器翻墙，可能容易让服务器被封禁。
> **当前部署形态默认就不在服务器上抓数据**（`INSTALL_PLAYWRIGHT_CHROMIUM=false`），数据要通过本地抓好后 scp DuckDB 文件上来（见第 8 章）。

---

## 1. MobaXterm 使用速成

### 1.1 下载安装

1. 浏览器打开 <https://mobaxterm.mobatek.net/download-home-edition.html>
2. 下载 **Home Edition (Installer edition)** —— 免费、足够用
3. 安装后双击启动

### 1.2 创建 SSH Session（连接 ECS）

1. 顶部菜单点 **Session**（会话）
2. 弹窗左上角点 **SSH**
3. 填四项：

| 字段 | 填什么 |
|------|--------|
| **Remote host** | 你的 ECS 公网 IP（如 `123.45.67.89`） |
| **Specify username** | 勾上，填 `root` |
| **Port** | `22`（默认） |
| **Advanced SSH settings → Use private key** | 如果用 SSH key 登录就勾上选私钥文件；用密码就不勾 |

4. 点 **OK**
5. 第一次连接会问 `Accept and Save?` → 点 **Accept**
6. 用密码登录的会提示输入密码（**输入时屏幕不显示，正常**）→ 输完回车
7. 看到 `root@xxx:~#` 提示符就连上了

> 💡 **保存密码**：MobaXterm 会问要不要保存密码，建议保存（仅本地，不会发给云端），下次连接免输入。

### 1.3 必备技巧 4 条

| 操作 | 做法 |
|------|------|
| **左侧文件管理** | 连上后左侧自动出现 SFTP 面板，可以拖拽上传/下载文件 |
| **多终端窗口** | 顶部 `View → MultiExec` 或 `Tile` 同时操作多个 session |
| **复制粘贴** | 选中文字自动复制；右键粘贴。**不要 Ctrl+C**（在 Linux 终端那会中断命令） |
| **断线自动重连** | `Settings → Configuration → SSH → SSH keepalive` 勾上 |

### 1.4 【了解即可，我们通过git直接在服务器上拉代码】把本地文件传到服务器

两种方式：

- **方式 A（最简单）**：左侧 SFTP 面板，从你 Windows 的资源管理器**直接拖文件进去**
- **方式 B（命令行）**：在本地 PowerShell 跑：
  ```powershell
  scp -r D:\some-local-dir root@你的IP:/opt/destination/
  ```

---

## 2. 阿里云 ECS 安全组配置（如果想了解云服务器可以看一下，否则，这一步可跳过）

ECS 默认只开 22 端口（SSH），HTTP/HTTPS 必须手动开放，否则浏览器访问不到。

### 操作步骤

1. 浏览器登录 <https://ecs.console.aliyun.com>
2. 左侧 **实例与镜像 → 实例**
3. 找到你的实例 → 点实例名进去
4. 切到 **安全组** 标签页
5. 点关联的安全组名字（一般叫 `sg-xxxxxxxx`）
6. **入方向 → 手动添加**，加 2 条：

| 端口范围 | 授权对象 | 描述 |
|---------|---------|------|
| `80/80` | `0.0.0.0/0` | HTTP |
| `443/443` | `0.0.0.0/0` | HTTPS |

7. 保存。**安全组规则秒级生效**，不用重启 ECS。

> ⚠️ 即使后期只用 HTTPS，也建议两个端口都开 —— Caddy 签 Let's Encrypt 证书需要 80。

---

## 3. 装 Docker（绕开 GFW）

> 国内 ECS 直连 `get.docker.com` 必然失败，**必须走阿里云镜像**。

### 3.1 在 MobaXterm 终端里跑（一行）

```bash
curl -fsSL https://get.docker.com | sh -s -- --mirror Aliyun
```

预期输出末尾：
```
+ sh -c docker version
Client: Docker Engine - Community
 Version: 27.x.x
Server: Docker Engine - Community
 Version: 27.x.x
```

### 3.2 配镜像加速器（**必做**，否则后面 `docker pull` 会超时）

```bash
cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://docker.nju.edu.cn"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "20m",
    "max-file": "3"
  }
}
EOF

systemctl daemon-reload
systemctl restart docker

# 验证
docker info | grep -A 5 "Registry Mirrors"
```

预期看到 4 个加速器地址被加载。

### 3.3 装 docker compose plugin（可能已随 Docker 一起装好）

```bash
docker compose version
```

如果提示找不到命令：
```bash
apt-get install -y docker-compose-plugin     # Ubuntu/Debian
# 或
yum install -y docker-compose-plugin         # CentOS/Anolis
```

---

## 4. 拉项目代码

```bash
# 装 git（一般已有）
apt-get install -y git || yum install -y git

# 选个目录放项目
mkdir -p /opt && cd /opt

# 克隆
git clone https://github.com/NoStayUpLate/CC.git
cd CC

# 验证目录结构
ls
```

应该看到：
```
backend/  Caddyfile  CLAUDE.md  deploy.sh  docker-compose.yml
docker-compose.dev.yml  frontend/  README.md  scripts/  ...
```

### 4.1 私有仓库怎么 clone

如果项目是私有仓库，需要 GitHub Personal Access Token：

1. 浏览器打开 <https://github.com/settings/tokens>
2. 点 **Generate new token (classic)**
3. 起名（如 `ecs-deploy`），权限只勾 `repo`
4. 复制生成的 `ghp_xxxx` 字符串
5. 在 ECS 上：
```bash
git clone https://你的GitHub用户名:ghp_xxx@github.com/owner/repo.git
```

---

## 5. 配置 .env.production

❗***注意：这一段需要根据你的项目环境进行配置，这里仅供参考，可通过CC询问你的项目如何配置。***❗

------

```bash
cd /opt/CC
chmod +x deploy.sh

# 复制样例
cp .env.production.example .env.production

# 用 vim 或 nano 编辑（vim 不会用就装 nano: apt install -y nano）
vim .env.production
```

### 必填字段对照表

| 字段 | 怎么填 | 备注 |
|------|--------|------|
| `JWT_SECRET` | **运行 `./deploy.sh secret` 生成的 64 位串** | 唯一必填项，空了后端启动失败 |
| `JWT_EXPIRE_HOURS` | 默认 8 即可 | |
| `COOKIE_SECURE` | HTTP 模式默认 `false`；HTTPS 时改 `true` | 必须与传输协议匹配 |
| `COOKIE_SAMESITE` | `lax` | 一般不动 |
| `AUTH_BACKEND` | `sqlite`（推荐，支持自助注册）/ `file`（写死账号） | |
| `AUTH_USERS` | file 模式下填 `用户名:bcrypt_hash`；sqlite 模式留空 | bcrypt 用 `python -m auth.cli hash 密码` 生成 |
| `REGISTRATION_CODE` | 自定一个长字符串（如 `team-2026-spring`） | 邀请码，团队内部分发 |
| `SCHEDULE_ENABLED` | 默认 `false`（境内 ECS 跨境抓不到） | 海外节点改 `true` 才有意义 |
| `INSTALL_PLAYWRIGHT_CHROMIUM` | 默认 `false`（生产不抓数据，省 ~700MB 镜像） | 想在容器里跑爬虫才改 `true` |

> ⚠️ **不再需要**：`DOMAIN` / `ADMIN_EMAIL`（无 Caddy）/ `CLICKHOUSE_*`（DuckDB 嵌入式无密码）。
> 历史 `.env.production` 里的这些行可以保留，pydantic 配了 `extra=ignore` 不会报错。

### 一键生成关键凭据

下面这段 **整段贴进终端**，会自动生成 JWT_SECRET 和邀请码并塞进 .env：

```bash
cd /opt/CC

# 生成
JWT=$(./deploy.sh secret)
INVITE_CODE="team-$(date +%Y%m)-$(openssl rand -hex 4)"

# 塞入 .env.production
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$JWT|" .env.production
sed -i "s|^REGISTRATION_CODE=.*|REGISTRATION_CODE=$INVITE_CODE|" .env.production

# 备份凭据到 root 主目录（仅 root 可读）
cat > /root/cc-secrets.txt <<EOF
JWT_SECRET=$JWT
REGISTRATION_CODE=$INVITE_CODE
生成时间: $(date)
EOF
chmod 600 /root/cc-secrets.txt

echo ""
echo "===== 注册第一个账号需要这个邀请码：====="
echo "$INVITE_CODE"
echo "（也可以随时 cat /root/cc-secrets.txt 查）"
```

---

## 6. 一键启动

```bash
cd /opt/CC

# 启动（瘦身版无 CH / 无 Chromium，1-3 分钟）
./deploy.sh up
```

启动完会自动跑健康检查。看到下面就成功：

```
[deploy] 容器状态：
NAME              IMAGE          STATUS
novel_backend     cc-backend     Up (healthy)
novel_frontend    cc-frontend    Up (healthy)

[ ✓ ] backend /health  → OK
[ ✓ ] frontend nginx   → OK
访问地址：http://<ECS公网IP>
```

> ⚠️ 如果是国内 ECS，第一次拉 base image (`python:3.11-slim` / `nginx:alpine`) 视网络速度可能慢。`backend/Dockerfile` 已把 apt / pip 源换成阿里云，构建本身只要几十秒。

---

## 7. 浏览器访问 + 注册第一个账号

### 7.1 访问

打开浏览器，地址栏**完整输入**：

```
http://你的ECS公网IP
```

注意：
- ⚠️ 必须有 `http://` 前缀，否则浏览器（特别是 Edge/Chrome）会自动升级为 https，但我们 HTTP 模式没证书 → ERR_SSL_PROTOCOL_ERROR
- 如果跳到 https 进不去 → 用**无痕窗口**（`Ctrl+Shift+N`）打开

### 7.2 关闭浏览器自动 HTTPS（一劳永逸）

**Edge**：
- 地址栏输 `edge://settings/privacy`
- 找到 **"使用自动 HTTPS 自动切换到更安全的连接"** → 关闭
- 重启浏览器

**Chrome**：
- 地址栏输 `chrome://settings/security`
- 找到 **"始终使用安全连接"** → 关闭

---

## 8. 上传本地数据到 DuckDB（可选）

刚部署完 DuckDB 是空的，登录进去看不到数据。两条路把数据填进来：

### 8.1 方案 A — 本地抓好后 scp 上去（推荐）

在你**本地**（能跑爬虫的机器）：

```bash
# 1. 跑爬虫填本地 DuckDB（任选一个平台，先抓 50 条试水）
cd backend && python -m uvicorn main:app --port 8000 &
curl -X POST http://localhost:8000/api/scrape -H 'Content-Type: application/json' \
  -d '{"platform":"wattpad","limit":50}'

# 2. 把 dashboard.duckdb 文件 scp 到服务器
scp backend/dashboard.duckdb root@<ECS-IP>:/opt/CC/dashboard.duckdb
```

在 ECS 上：

```bash
cd /opt/CC

# 找 backend_data 卷的真实名（compose project 名 + 卷名）
VOL=$(docker volume ls --format '{{.Name}}' | grep backend_data | head -1)
echo "目标卷: $VOL"

# 把上传的文件搬进卷里
docker compose --env-file .env.production stop backend
docker run --rm -v "$VOL":/data -v /opt/CC:/host alpine sh -c \
  "cp /host/dashboard.duckdb /data/dashboard.duckdb && ls -lh /data/"
docker compose --env-file .env.production start backend
sleep 5
./deploy.sh status
```

### 8.2 方案 B — 从本地 ClickHouse 一次性迁移

如果你之前在本地跑过 ClickHouse、积累了数据，先在本地跑迁移脚本生成 DuckDB 文件：

```bash
pip install clickhouse-connect    # 一次性
python scripts/migrate_ch_to_duckdb.py --reset
# 输出：novels 621 行 / dramas 236 行 等
```

然后按 8.1 的 scp + docker run 流程把生成的 `backend/dashboard.duckdb` 传上去。

---

## 9. 常见踩坑 FAQ（基于真实经历）

### Q1：`curl https://get.docker.com` 一直 timeout

**原因**：GFW 拦了 docker.com
**解决**：用 `--mirror Aliyun` 参数（见 §3.1）

### Q2：`docker pull` 卡死或超时

**原因**：没配镜像加速器
**解决**：`/etc/docker/daemon.json` 配 registry-mirrors（见 §3.2）

### Q3：构建过程中拉 base image (`python:3.11-slim`) 巨慢

**原因**：境内访问 Docker Hub 不稳
**解决**：`/etc/docker/daemon.json` 配 registry-mirrors（见 §3.2），瘦身后已经不再装 Chromium / Playwright 系统依赖，构建主要时间就在 base image 上

### Q4：浏览器报 `ERR_SSL_PROTOCOL_ERROR`

**原因**：浏览器自动升级 HTTPS，但我们 HTTP 模式没证书
**解决**：地址栏完整输入 `http://` 前缀；或关浏览器的"自动 HTTPS"（见 §7.2）

### Q5：登录后立即被踢回登录页

**原因**：`COOKIE_SECURE=true` 但你是 HTTP 访问，浏览器拒种 cookie
**解决**：确认 `.env.production` 里 `COOKIE_SECURE=false`，然后：
```bash
./deploy.sh restart
docker compose --env-file .env.production exec backend env | grep COOKIE
# 应该显示 COOKIE_SECURE=false
```

### Q6：浏览器看不到 `223.4.250.171` 等公网 IP

**原因**：阿里云安全组没开 80 端口
**解决**：见 §2 的安全组配置

### Q7：登录后看到空看板（数据为 0）

**原因**：DuckDB 是新建的、空的
**解决**：见 §8 的两个数据填充方案（本地抓好 scp 上来，或从历史 CH 迁移）

### Q8：爬虫报 `Network is unreachable` 或全部超时（如果你打开了 Chromium）

**原因**：国内 ECS 出口对境外站点（Wattpad/Royal Road/...）几乎不可达
**解决**：
- 长期：换阿里云**香港/新加坡**节点
- 短期：接境外代理（注意合规风险）
- 替代：本地抓好 scp 上来（推荐）

### Q9：`docker compose exec` 看到一堆 `WARN ... is not set`

**原因**：跑 docker compose 命令时漏了 `--env-file .env.production`
**解决**：所有 docker compose 操作都加 `--env-file .env.production`，或者用封装好的 `./deploy.sh` 命令

### Q10：bcrypt 报 `password cannot be longer than 72 bytes`

**原因**：bcrypt 5.x 与 passlib 不兼容
**解决**：本项目已经改用 bcrypt 直接调用，不再依赖 passlib（已修）

### Q11：`./deploy.sh` 提示找不到命令

**原因**：可执行权限丢了（Windows clone 出来常见）
**解决**：`chmod +x deploy.sh`

### Q12：服务器上有历史 ClickHouse 容器 / 卷残留怎么清

**原因**：早期版本部署过 CH 容器，瘦身后这些资源不会自动清
**解决**：
```bash
# 看历史卷
docker volume ls | grep clickhouse
# 确认数据已不需要后清掉
docker volume rm cc_clickhouse_data cc_clickhouse_logs   # 名字按你实际看到的
```

---

## 10. 日常运维命令速查

所有命令在 `/opt/CC` 下执行：

```bash
# 看运行状态 + 健康检查 + 访问地址
./deploy.sh status

# 跟随日志
./deploy.sh logs              # 所有服务
./deploy.sh logs backend      # 只看 backend（也可换 frontend）

# 生命周期
./deploy.sh up                # 启动（也用作首次部署）
./deploy.sh restart           # 重启全部
./deploy.sh down              # 停止（数据卷保留）
./deploy.sh update            # git pull → 重建镜像 → 重启 → 清理悬挂镜像

# 杂项
./deploy.sh secret            # 生成 JWT_SECRET（仅打印）
./deploy.sh help              # 完整说明

# DuckDB 进数据库交互查询（嵌入式没独立 cli，借 backend 容器跑 python）
docker compose --env-file .env.production exec backend python -c \
  "import duckdb; c=duckdb.connect('/data/dashboard.duckdb'); \
   print('novels:', c.execute('SELECT count(*) FROM novels').fetchone()); \
   print('dramas:', c.execute('SELECT count(*) FROM dramas').fetchone())"

# CLI 管理 SQLite 用户
docker compose --env-file .env.production exec backend python -m auth.cli list
docker compose --env-file .env.production exec backend python -m auth.cli add-user xxx -p yyy
docker compose --env-file .env.production exec backend python -m auth.cli passwd xxx -p 新密码
docker compose --env-file .env.production exec backend python -m auth.cli delete xxx

# 备份 backend_data 卷（同时含 SQLite 用户库 + DuckDB 数据库）
VOL=$(docker volume ls --format '{{.Name}}' | grep backend_data | head -1)
docker run --rm -v "$VOL":/data -v $(pwd):/backup alpine \
  tar czf /backup/backup-$(date +%Y%m%d).tgz /data/

# 想在容器里跑爬虫？需要重 build 装 Chromium（约 +700MB）
docker compose --env-file .env.production build \
  --build-arg INSTALL_PLAYWRIGHT_CHROMIUM=true backend
docker compose --env-file .env.production up -d backend
```

---

## 11. 后续可选：买域名 + HTTPS

瘦身版默认 HTTP-only。要加 HTTPS：

1. 买域名 + A 记录指向 ECS 公网 IP，安全组开 443 入站
2. `git log --all --oneline -- docker-compose.yml` 找瘦身前包含 Caddy 的版本，把 `caddy:` 服务段拷回当前 `docker-compose.yml`
3. `.env.production` 加 `DOMAIN=your-domain.com` + `ADMIN_EMAIL=ops@your-domain.com`
4. `.env.production` 改 `COOKIE_SECURE=true`
5. `./deploy.sh restart`，Caddy 启动后会自动签 Let's Encrypt 证书

---

## 附录 A：本教程未覆盖的事

- **CI/CD 自动部署**：当前需要手工 `./deploy.sh update`，可以接 GitHub Actions 自动 push 触发
- **多副本 / 负载均衡**：单机 docker compose 适合到 50 并发用户级别，更大需 K8s（DuckDB 单文件不支持多进程写入，要拆要先换 PostgreSQL）
- **数据库备份**：见 §10 的 `tar czf` 命令
- **监控告警**：Prometheus + Grafana 可以接，但本项目暂未做

---

## 附录 B：MobaXterm 进阶技巧

| 场景 | 操作 |
|------|------|
| 同时给多个 ECS 跑同一条命令 | `Tools → MultiExec` |
| 把本地脚本传上去再跑 | 拖到左侧 SFTP 面板 → 终端 `bash 脚本名.sh` |
| 后台执行长任务防止断线丢失 | `nohup ./deploy.sh up &` 或装 `tmux`/`screen` |
| 多个 session 拆分窗口看 | 顶部 `View → Vertical/Horizontal split` |
| 自动保存 session 历史 | 默认开启，菜单 `Sessions → 历史会话` |
