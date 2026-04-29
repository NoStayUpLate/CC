---
name: project-hardening
description: |
  【通用 / 跨项目】给任何代码工程做"健壮性 + 可维护性"审计与加固。无关具体技术栈（Python/Node/Go/Rust 都适用），不依赖本仓库任何文件，可直接复制到其他项目的 .claude/skills/ 下使用。
  触发关键词（任一命中即激活）：
    中文 — 架构审计、加固项目、整理代码、提升健壮性、防泄密、上云前梳理、新项目脚手架、把这个工程改造一下、代码规范化
    英文 — harden project, audit architecture, secrets scan, refactor scaffolding, bootstrap repo, code review checklist
  作用：按 8 步审计清单逐项扫描项目，定位常见架构隐患（硬编码密钥、配置裸奔、层职责混乱、缺 CLAUDE.md、缺一键脚本等），给出**可执行的具体修复步骤**，最后输出一份"分项打分 + Top 3 高 ROI 改造建议"报告。
---

# Project Hardening — 工程加固与可维护性审计

> **设计目标**：与具体栈无关。任何语言、任何框架的项目都可以扔给 AI 跑一遍。
> **使用方式**：把整个 `project-hardening/` 目录拷到目标项目的 `.claude/skills/` 下即可。

---

## 0. 何时触发

满足以下任一情况就启动：
- 用户要求"代码评审 / 架构审计 / 上云前梳理 / 项目改造 / 健壮性提升"
- 接手新项目、打算长期维护它
- 即将首次 `git push` 到远程仓库（防泄密尤其关键）
- 项目里出现以下症状之一：硬编码密码 / 一改字段全栈崩 / 新人上手要 1 周 / 部署需要 N 步操作

如果用户给的是具体小问题（"修个 bug"），**不要**触发本 skill。

---

## 1. 工作流

按下列 **8 步**顺序逐项审计。每步先**只读不写**，把发现汇总后再问用户是否动手。每步结尾都有「✓ 通过 / ⚠ 部分 / ✗ 缺失」三档自评。

最后输出**整体报告**（见 §10）。

---

## Step 1 — 🔐 凭据与密钥审计（最高优先级，永远先做）

> **一旦泄密就回不来了**：即使后来从 git 历史删除，公开仓库被爬虫存档过的概率接近 100%。

### 检查项

```
1.1  是否有 .gitignore？
1.2  .gitignore 是否覆盖了：.env*、*.db、*.sqlite、node_modules/、.venv/、IDE 配置、密钥文件 (*.pem/*.key/.ssh/)
1.3  代码里有无硬编码：
       - 密码 / token / API key
       - 真实 IP（尤其 RFC1918 内网段：10.* / 172.16-31.* / 192.168.*）
       - 真实邮箱 / 域名 / Webhook URL（视项目敏感度）
1.4  配置类（config.py / config.js / settings.toml ...）的"默认值"是否是真实凭据？
1.5  示例配置（.env.example / config.example.*）里是不是占位符？
1.6  依赖清单（requirements.txt / package-lock.json / Pipfile.lock）是否在版本控制？
1.7  即将 push 的 staged 文件是否泄密？跑 `git diff --cached | grep -iE 'password|secret|token|api[_-]?key'`
```

### 高频踩雷扫描脚本（任何项目通用）

```bash
# 找硬编码密钥/密码（粗扫，仍需人工核实）
grep -rEn --include='*.py' --include='*.js' --include='*.ts' --include='*.go' --include='*.rb' \
  -e '(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*["'\'']\w{8,}' \
  --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git .

# 找硬编码内网 IP
grep -rEn --include='*.py' --include='*.js' --include='*.go' --include='*.yml' --include='*.yaml' \
  -e '\b(10\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)[0-9]+\.[0-9]+\b' \
  --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git .

# 找 AWS / GitHub token 模式
grep -rEn -e 'AKIA[0-9A-Z]{16}' -e 'ghp_[A-Za-z0-9]{36}' -e 'sk_live_[A-Za-z0-9]+' .
```

### 修复模板

| 发现 | 修复 |
|------|------|
| `password = "real_password"` 在代码里 | 改用 env var，代码里默认值用空串；启动时 fail-fast 检测 |
| `.env` 已被 commit | 立即轮换该密钥；用 `git filter-branch` / [BFG](https://rtyley.github.io/bfg-repo-cleaner/) 清历史；通知所有 fork |
| 缺 `.gitignore` | 用 [github/gitignore](https://github.com/github/gitignore) 模板 + 项目特定补充 |
| 缺 `.env.example` | 列出所有 env var，**值用占位符**，每行加注释说明用途 |

✓ / ⚠ / ✗：__

---

## Step 2 — ⚙ 配置纪律

### 检查项

```
2.1  是否有强类型配置容器（pydantic-settings / viper / dotenv-loader / Spring @ConfigurationProperties）？
2.2  是否区分开发 / 生产 / 测试三套配置？
2.3  关键 env var（DB 密码 / JWT secret / 加密 key）缺失时是 fail-fast 还是悄悄默认？
2.4  是否有 .env.example / config.example.*，且与 production 字段集严格一致？
2.5  config 文件本身有没有写注释解释每个字段的用途、取值范围、修改影响？
```

### 反模式

- ❌ `os.getenv("FOO", "production_default")` — 默认值直接是真生产值
- ❌ "新增字段时 dev 改了忘了改 prod" — 缺机制保证字段对齐
- ❌ "配置写在 30 个 yaml 里散落各处" — 应集中到一个 source of truth

### 修复模板

```python
# Python 推荐用 pydantic-settings
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    db_password: str = ""           # 必填，空串触发 fail-fast
    jwt_secret: str = ""
    cookie_secure: bool = False
    class Config: env_file = ".env"

settings = Settings()

# 启动入口加 fail-fast
if not settings.db_password or not settings.jwt_secret:
    raise RuntimeError("DB_PASSWORD / JWT_SECRET 未配置")
```

✓ / ⚠ / ✗：__

---

## Step 3 — 🏗 分层架构与单一职责

> 目标：每个文件 / 模块的"修改原因"只有一个。

### 检查项

```
3.1  HTTP / API 处理函数是否"很薄"（只做参数校验 + 调 service）？
3.2  业务逻辑是否独立成 service / usecase 层？
3.3  数据访问是否独立（无 SQL 散落在 handler / template 里）？
3.4  层与层之间的契约是否显式（typed model / dataclass / interface）？
3.5  每层有没有"它不该做但做了"的事？
        - DB 层在算业务规则
        - API handler 在拼 SQL
        - 前端在重算后端已计算的指标
```

### 典型分层模板

```
┌─────────────────┐
│  API / Handler  │  ← 只做：HTTP I/O + 参数校验 + 调用 service
└────────┬────────┘
         │
┌────────▼────────┐
│    Service      │  ← 业务逻辑：编排 / 事务 / 校验业务规则
└────────┬────────┘
         │
┌────────▼────────┐
│  Repository     │  ← 数据访问：DDL / CRUD / 查询，无业务知识
└────────┬────────┘
         │
┌────────▼────────┐
│   DB / Cache    │  ← 真正的存储
└─────────────────┘

每层之间用 typed model 传递（Pydantic / dataclass / TypedDict）
```

### 修复策略

发现 handler 里有 SQL → 抽到 repository
发现 service 里在解析 HTTP query → 抽到 handler
发现"加一个字段要改 5 处"→ 用配置/契约集中

✓ / ⚠ / ✗：__

---

## Step 4 — 📖 CLAUDE.md（AI 上下文工程）

> AI agent 来到一个陌生项目，能否在 30 秒内知道**怎么不踩坑**？

### 必备段落

| # | 段落 | 内容 |
|---|------|------|
| 1 | 项目摘要 | 1 段话：做什么 + 主技术栈 + 数据流图 |
| 2 | 目录速查 | 表格：每个关键文件 / 目录的用途 |
| 3 | 常用命令 | 一段 bash：启动 / 测试 / 构建 / 部署 |
| 4 | **⚠️ 硬约束** | 编号列表：「代码强制成立但不显然」的契约（禁止 X / 必须 Y / 字段四处同步等）|
| 5 | 数据契约 | 关键模型字段表：类型 + 缺失值规则 |
| 6 | Skill 索引 | 列出 `.claude/skills/*/SKILL.md` 入口 |
| 7 | 协作约定 | 探索性问题先建议 / 不主动写文档 / 破坏性操作先确认 |

### 反模式

- ❌ 复制粘贴 README 内容（README 给人，CLAUDE.md 给 AI，两者关注不同）
- ❌ 写满"best practice 平台型废话"
- ❌ 长到 300 行没人读 — **目标 100-150 行内**
- ❌ 链接全是绝对路径 / 死链
- ❌ 列了一堆但没说"为什么不能这样"

### 衡量标准

新会话开一个 AI，**只给 CLAUDE.md**，问它："如何新增一个 X 功能？" → 它能引用到正确的 skill / 关键文件，且**主动拒绝**踩雷写法（如硬编码密钥），就是合格。

✓ / ⚠ / ✗：__

---

## Step 5 — 🔧 Skills（可重复工作流编码）

> 团队里"做了 3 次以上的事"应该编码成 skill。

### 何时该建一个新 skill

- 工作流跨多文件 / 需要多处同步（漏一处就报错）
- 有"非显然的步骤"容易被忘（如：注册到某 registry）
- 已经成功做过 2-3 次，模式清晰

### SKILL.md 标准结构

```markdown
---
name: <kebab-case>
description: |
  【场景标签】一句话说明。
  触发关键词（中英）：xxx
  作用：强制按 X 模板，避免 Y 错误。
---

# Skill 标题

## 何时触发
（具体场景，不要"通用"）

## 决策树 / 选哪个分支

## 落地清单（N 步）
Step 1 — ...
Step 2 — ...

## 必须避免的反模式

## 提交前自检清单
- [ ] ...
```

### 反模式

- ❌ skill 内容太空泛（"请遵循最佳实践"）
- ❌ skill 装太多无关关键词（触发面太广反而被忽略）
- ❌ 同一个项目 20 个 skill 互相重叠

✓ / ⚠ / ✗：__

---

## Step 6 — 🛡 纵深防御（让关键错误不可能发生，而非不太可能）

> "靠人记得"= 早晚会忘。

### 检查项

```
6.1  鉴权：是用 middleware/decorator 全局守卫，还是每个 handler 各自加？
        ✓ 推荐全局 + 显式排除 (e.g., FastAPI app.include_router(r, dependencies=[Depends(require_user)]))
        ✗ 反例 每个 handler 顶部加 if not request.user: raise 403

6.2  数据库迁移：是否幂等？(IF NOT EXISTS / DROP IF EXISTS / ALTER ADD COLUMN IF NOT EXISTS)
        ✗ 反例 "首次部署时手工 SQL，后人不知道"

6.3  关键配置缺失：fail-fast 还是 silent default？
        ✓ 启动入口直接 raise

6.4  Docker / k8s：服务依赖是否有 healthcheck + depends_on conditions？
        ✗ 反例 backend 启动时 DB 还没 ready，连接失败崩
        ✓ 用 healthcheck + depends_on: condition: service_healthy

6.5  备份：备份策略是否文档化 + 测试过恢复？
```

### 反模式

- ❌ "上线前别忘了改 X" — 这种每次都会忘
- ❌ "管理员需要手工跑这条 SQL" — 应该写成迁移
- ❌ "production 必须设这个 env，否则会出事" — 应该 fail-fast

✓ / ⚠ / ✗：__

---

## Step 7 — 🚀 一键运维脚本

> 任何"团队成员需要做的常见操作"应该是**一条命令**。

### 必备覆盖

| 场景 | 推荐命令形式 |
|------|------------|
| 本地开发启动 | `./dev.sh` 或 `make dev` |
| 服务器部署/更新 | `./deploy.sh up` / `update` / `down` / `logs` / `status` |
| 跑测试 | `./test.sh` 或 `make test`（含 lint / type-check） |
| 数据库迁移 | `./migrate.sh up/down` |
| 用户/凭据管理 | `./admin.sh add-user xxx` |

### 脚本必须包含

- ✓ 预检查：依赖是否装好、关键 env 是否配齐、网络是否通
- ✓ 友好错误：缺什么直接给可执行的修复命令
- ✓ 子命令分明：`up / down / restart / logs / status / update`
- ✓ 颜色区分：log / ok / warn / error 一眼能区分
- ✓ 幂等：`up` 重复跑不会出错

### 反模式

- ❌ "看 README 第 4 节第 3 段" — 应该一条命令
- ❌ "这条命令我们组只有 leader 知道" — 应该编入脚本
- ❌ 脚本失败但 exit 0 — 必须 `set -euo pipefail`

✓ / ⚠ / ✗：__

---

## Step 8 — 📚 文档分层

> 一份文档不可能服务所有读者；按受众分层。

| 受众 | 文件 | 内容 | 长度 |
|------|------|------|------|
| 用户 / 部署者 | `README.md` | 安装、启动、API、FAQ | 不限 |
| AI agent（写代码） | `CLAUDE.md` | 骨架 + 硬约束 + skill 索引 | < 150 行 |
| AI agent（重复工作流） | `.claude/skills/*/SKILL.md` | 步骤化 playbook | 各自 100-300 行 |
| 未来维护者（决策） | `docs/adr/*.md`（可选） | **为什么**这么设计，不是**做了什么** | 每条 < 1 页 |
| 运维 | `docs/runbook.md`（可选） | 故障应急 SOP | 看现场需求 |

### 检查项

```
8.1  README 是不是写给"第一次看见这个项目的人"，而不是"项目作者自己回忆用"？
8.2  CLAUDE.md 是不是 AI-first（短、硬约束、指针化）？
8.3  CLAUDE.md 是否在 README / SKILL.md / 关键源码之间互相链接，而不是复制？
8.4  长期决策（如"为什么用 X 不用 Y"）是否记录？
```

✓ / ⚠ / ✗：__

---

## 9. 跨项目通用 .gitignore 起步模板

```gitignore
# 环境与密钥
.env
.env.*
!.env.example
!.env.*.example
*.pem
*.key
.secrets/

# 数据库 / 用户 / 缓存
*.db
*.sqlite*
*.dump

# 各语言依赖
node_modules/
.venv/
venv/
__pycache__/
*.py[cod]
target/        # Rust / Java
vendor/        # Go / PHP

# 构建产物
dist/
build/
out/
*.log

# IDE / 系统
.vscode/
.idea/
.DS_Store
Thumbs.db

# AI 工具个人配置（项目级 skill 应保留）
.claude/settings.local.json
.claude/local/
```

---

## 10. 最终报告格式

审计完成后，把结果按下列模板汇报给用户：

```markdown
# 项目加固审计报告

## 分项打分

| 项 | 得分 | 关键问题 |
|---|------|----------|
| 1. 凭据与密钥 | ✓✓✓ / ✓ / ✗ | ... |
| 2. 配置纪律 | ... | ... |
| 3. 分层架构 | ... | ... |
| 4. CLAUDE.md | ... | ... |
| 5. Skills | ... | ... |
| 6. 纵深防御 | ... | ... |
| 7. 一键运维 | ... | ... |
| 8. 文档分层 | ... | ... |

## 🔴 高危（建议立即修）

1. <最严重 1-3 条，含具体文件:行 + 修复命令>

## 🟡 Top 3 高 ROI 改造建议

| # | 改造 | 工作量 | 收益 |
|---|------|--------|------|
| 1 | ... | 半小时 | 杜绝整类问题 |
| 2 | ... | 1 天 | ... |
| 3 | ... | 半天 | ... |

## 🟢 已经做得好的地方

（正向反馈，让用户知道哪些不要乱动）

## 下一步

询问用户：「先修高危的还是先做 Top 1 改造？」**等用户决定再动手**。
```

---

## 11. 反元信息：本 skill 自身的限制

- 本 skill **只做审计 + 提议**，**不会自动改代码**，所有改动必须用户拍板
- 跨语言模板默认偏 Python / Node 生态；其他语言（Go / Rust / Java / PHP）的具体命令需要 AI 临场调整
- 不替代真正的 code review / SAST 工具（Semgrep / Trivy / SonarQube），只是**第一道筛子**
- 如果项目已经在生产运行，**Step 1 凭据扫描发现已 commit 的密钥**，必须先轮换再做其他事

---

## 12. 复用到其他项目

```bash
# 把整个 project-hardening 目录拷到新项目
cp -r .claude/skills/project-hardening /path/to/other-project/.claude/skills/

# 或者 git submodule（共享更新）
git submodule add https://github.com/.../skills .claude/skills
```

复制时**不带任何项目特定文件**，本 skill 完全自包含。
