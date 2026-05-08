# 上云部署完整教程（阿里云 ECS）

> 本教程基于实际部署经历整理，给团队同事按图施工用。**第一次部署预计 60-90 分钟**。
> 部署目标：把项目从 GitHub 克隆到云服务器，跑起完整的 docker compose 栈，浏览器能访问。
>
> 适用范围：本项目（FastAPI + React + ClickHouse），但**部署流程的前 5 章对任何 docker compose 项目通用**。第 6 章特别说明**数据库选择**（ClickHouse / SQLite / PostgreSQL）的差异。

---

## 目录

- [0. 准备工作清单](#0-准备工作清单)
- [1. MobaXterm 使用速成](#1-mobaxterm-使用速成)
- [2. 阿里云 ECS 安全组配置](#2-阿里云-ecs-安全组配置)
- [3. 装 Docker（绕开 GFW）](#3-装-docker绕开-gfw)
- [4. 拉项目代码](#4-拉项目代码)
- [5. 配置 .env.production](#5-配置-envproduction)
- [6. ⭐ 数据库选择：ClickHouse / SQLite / PostgreSQL](#6--数据库选择clickhouse--sqlite--postgresql)
- [7. 一键启动](#7-一键启动)
- [8. 浏览器访问 + 注册第一个账号](#8-浏览器访问--注册第一个账号)
- [9. 常见踩坑 FAQ（基于真实经历）](#9-常见踩坑-faq基于真实经历)
- [10. 日常运维命令速查](#10-日常运维命令速查)
- [11. 后续可选：买域名 + HTTPS](#11-后续可选买域名--https)

---

## 0. 准备工作清单

开始前确保你有：

- [ ] **阿里云 ECS 实例**（最低配置 2 核 4G、40G 系统盘；推荐 Ubuntu 22.04+ 或 Anolis 8）
- [ ] **ECS 的公网 IP** + **登录密码（或 SSH key）**
- [ ] **本地装好 MobaXterm**（Windows 用户，下载：<https://mobaxterm.mobatek.net/download.html>，免费版够用）
- [ ] **GitHub 仓库地址**（自己创建，利用国内的gitee也可以），如果是私有仓库还需要 PAT

> ⚠️ **国内 ECS 警告**：因为技术部署的服务器是杭州的，无法在线上运行爬虫代码。建议不要尝试服务器翻墙，可能容易让服务器被封禁。

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
| `DOMAIN` | 你的域名（如 `bi.example.com`），**没有就先填 `localhost` 占位** | 没域名时第 11 章会教怎么改 HTTP 模式 |
| `ADMIN_EMAIL` | 你的邮箱 | Caddy 签证书时联系你用 |
| `JWT_SECRET` | **运行 `./deploy.sh secret` 生成的 64 位串** | 不能为空，否则后端启动失败 |
| `JWT_EXPIRE_HOURS` | 默认 8 即可 | |
| `COOKIE_SECURE` | **`true`（HTTPS）/ `false`（HTTP 模式临时调试）** | 必须与传输协议匹配 |
| `COOKIE_SAMESITE` | `lax` | 一般不动 |
| `AUTH_BACKEND` | `sqlite`（推荐，支持自助注册）/ `file`（写死账号） | |
| `AUTH_USERS` | file 模式下填 `用户名:bcrypt_hash`；sqlite 模式留空 | bcrypt 用 `python -m auth.cli hash 密码` 生成 |
| `REGISTRATION_CODE` | 自定一个长字符串（如 `team-2026-spring`） | 邀请码，团队内部分发 |
| `CLICKHOUSE_*` | **见下一章 §6** | 取决于数据库选型 |

### 一键生成关键凭据

下面这段 **整段贴进终端**，会自动生成 JWT_SECRET、CH 密码、邀请码并塞进 .env：

```bash
cd /opt/CC

# 生成
JWT=$(./deploy.sh secret)
CH_PASS=$(./deploy.sh secret)
INVITE_CODE="team-$(date +%Y%m)-$(openssl rand -hex 4)"

# 塞入 .env.production
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$JWT|" .env.production
sed -i "s|^CLICKHOUSE_PASSWORD=.*|CLICKHOUSE_PASSWORD=$CH_PASS|" .env.production
sed -i "s|^REGISTRATION_CODE=.*|REGISTRATION_CODE=$INVITE_CODE|" .env.production

# 备份凭据到 root 主目录（仅 root 可读）
cat > /root/cc-secrets.txt <<EOF
JWT_SECRET=$JWT
CLICKHOUSE_PASSWORD=$CH_PASS
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

## 6. ⭐ 数据库选择：ClickHouse / SQLite / PostgreSQL

> **关键决策点**。本项目原生设计是 ClickHouse，换其他数据库需要改代码。

### 6.0 决策表

| 你的情况 | 选什么 | 工作量 |
|---------|--------|--------|
| 跟我们用一样的项目（这个看板） | **ClickHouse 同栈**（默认） | 0（已配置好） |
| 已有外部 ClickHouse（VPC / 自建） | ClickHouse 外部 | 改 1 个 env 字段 |
| 你的另一个项目，本来就用 SQLite | SQLite | 取决于你项目本身 |
| 你的另一个项目，用 PostgreSQL | PostgreSQL 同栈 | 改 docker-compose |

### 6.1 方案 A — ClickHouse 

本项目 `docker-compose.yml` 已经预置 `clickhouse` 服务，**什么都不用改**，`.env.production` 填：

```env
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=8123
CLICKHOUSE_DATABASE=analysis
CLICKHOUSE_USERNAME=app
CLICKHOUSE_PASSWORD=<上一章自动生成的密码>
```

ClickHouse 容器会自动用 `app` 用户和 `analysis` 库初始化，backend 启动时自动建表。

**资源占用**：空载 ~200MB 内存，10万行数据约 500MB 磁盘。

### 6.2 方案 B — SQLite

#### 如果你的**另一个**项目本来就用 SQLite，部署做法

SQLite 是嵌入式数据库，**不需要单独容器**。直接在 backend 容器里挂卷：

```yaml
# docker-compose.yml 里 backend 服务的 volumes
volumes:
  - ./data:/app/data    # SQLite 文件存这里
```

backend 代码用 `sqlite:///app/data/myapp.db` 连接即可。备份只需 `tar czf backup.tgz ./data`。

---

## 7. 一键启动

```bash
cd /opt/CC

# 没域名时先临时改 HTTP 模式（详见 §11 的"无域名"说明）
sed -i 's|{$DOMAIN} {|:80 {|' Caddyfile
sed -i 's|^COOKIE_SECURE=.*|COOKIE_SECURE=false|' .env.production
grep -q "^COOKIE_SECURE=" .env.production || echo "COOKIE_SECURE=false" >> .env.production

# 启动！首次约 10-15 分钟（拉镜像 + 构建前端 + 装 Playwright）
./deploy.sh up
```

启动完会自动跑健康检查。看到下面就成功：

```
[ ✓ ] backend /health  → OK
[ ✓ ] frontend nginx   → OK
访问地址：...
```

> ⚠️ 如果是国内 ECS，构建过程中拉境外资源（Debian apt 源、Playwright Chromium）会很慢。本项目 `backend/Dockerfile` 已经全部换成阿里云镜像，预期 10-15 分钟完成。

---

## 8. 浏览器访问 + 注册第一个账号

### 8.1 访问

打开浏览器，地址栏**完整输入**：

```
http://你的ECS公网IP
```

注意：
- ⚠️ 必须有 `http://` 前缀，否则浏览器（特别是 Edge/Chrome）会自动升级为 https，但我们 HTTP 模式没证书 → ERR_SSL_PROTOCOL_ERROR
- 如果跳到 https 进不去 → 用**无痕窗口**（`Ctrl+Shift+N`）打开

### 8.2 关闭浏览器自动 HTTPS（一劳永逸）

**Edge**：
- 地址栏输 `edge://settings/privacy`
- 找到 **"使用自动 HTTPS 自动切换到更安全的连接"** → 关闭
- 重启浏览器

**Chrome**：
- 地址栏输 `chrome://settings/security`
- 找到 **"始终使用安全连接"** → 关闭

---

## 9. 常见踩坑 FAQ（基于真实经历）

### Q1：`curl https://get.docker.com` 一直 timeout

**原因**：GFW 拦了 docker.com
**解决**：用 `--mirror Aliyun` 参数（见 §3.1）

### Q2：`docker pull` 卡死或超时

**原因**：没配镜像加速器
**解决**：`/etc/docker/daemon.json` 配 registry-mirrors（见 §3.2）

### Q3：apt-get 下载 Playwright 依赖巨慢（半小时只下 3 个包）

**原因**：Debian 源走 deb.debian.org，国内访问慢
**解决**：本项目 `backend/Dockerfile` 已经换成阿里云源，**确认你拉的是最新代码**（`git pull`）

### Q4：浏览器报 `ERR_SSL_PROTOCOL_ERROR`

**原因**：浏览器自动升级 HTTPS，但我们 HTTP 模式没证书
**解决**：地址栏完整输入 `http://` 前缀；或关浏览器的"自动 HTTPS"（见 §8.2）

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

### Q7：爬虫报 `Network is unreachable` 或全部超时

**原因**：国内 ECS 出口对境外站点（Wattpad/Royal Road/...）几乎不可达
**解决**：
- 长期：换阿里云**香港/新加坡**节点
- 短期：接境外代理（注意合规风险）
- 替代：塞假数据/dump 数据先验证 UI

### Q8：`docker compose exec` 看到一堆 `WARN ... is not set`

**原因**：跑 docker compose 命令时漏了 `--env-file .env.production`
**解决**：所有 docker compose 操作都加 `--env-file .env.production`，或者用封装好的 `./deploy.sh` 命令

### Q9：bcrypt 报 `password cannot be longer than 72 bytes`

**原因**：bcrypt 5.x 与 passlib 不兼容
**解决**：本项目已经改用 bcrypt 直接调用，不再依赖 passlib（已修）

### Q10：`./deploy.sh` 提示找不到命令

**原因**：可执行权限丢了（Windows clone 出来常见）
**解决**：`chmod +x deploy.sh`

---

## 10. 日常运维命令速查

所有命令在 `/opt/CC` 下执行：

```bash
# 看运行状态 + 健康检查 + 访问地址
./deploy.sh status

# 跟随日志
./deploy.sh logs              # 所有服务
./deploy.sh logs backend      # 只看 backend（也可换 frontend / caddy / clickhouse）

# 生命周期
./deploy.sh up                # 启动（也用作首次部署）
./deploy.sh restart           # 重启全部
./deploy.sh down              # 停止（数据卷保留）
./deploy.sh update            # git pull → 重建镜像 → 重启 → 清理悬挂镜像

# 杂项
./deploy.sh secret            # 生成 JWT_SECRET（仅打印）
./deploy.sh help              # 完整说明

# 进 ClickHouse 客户端交互查询
docker compose --env-file .env.production exec clickhouse \
  clickhouse-client --user app --password "$(grep ^CLICKHOUSE_PASSWORD .env.production | cut -d= -f2)"

# CLI 管理 SQLite 用户
docker compose --env-file .env.production exec backend python -m auth.cli list
docker compose --env-file .env.production exec backend python -m auth.cli add-user xxx -p yyy
docker compose --env-file .env.production exec backend python -m auth.cli passwd xxx -p 新密码
docker compose --env-file .env.production exec backend python -m auth.cli delete xxx
```

---

## 附录 A：本教程未覆盖的事

- **CI/CD 自动部署**：当前需要手工 `./deploy.sh update`，可以接 GitHub Actions 自动 push 触发
- **多副本 / 负载均衡**：单机 docker compose 适合到 50 并发用户级别，更大需 K8s
- **数据库备份**：`docker run --rm -v <项目>_clickhouse_data:/data -v $(pwd):/backup alpine tar czf /backup/ch-backup.tgz /data`
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
