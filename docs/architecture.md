# 车修宝（ChexiuBao）技术架构方案

> 版本：v0.3 · 2026-09-07  
> 代码仓库：**前后端分仓（Multi-repo）**  
> 部署方式：**不使用 Docker**，本地原生运行 + 云托管服务

---

## 1. 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端层                                 │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│  PC Web 管理端 │  移动 H5/App  │  微信小程序   │  工位大屏（二期）    │
│  (React)      │  (React/RN)  │  (Taro)      │  (React)           │
└──────┬───────┴──────┬───────┴──────┬───────┴─────────┬──────────┘
       │              │              │                  │
       └──────────────┴──────┬───────┴──────────────────┘
                             │ HTTPS / WSS
                    ┌────────▼────────┐
                    │   API Gateway   │
                    │   (Nginx/Kong)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   后端服务       │
                    │   (FastAPI)     │
                    │                 │
                    │  ┌───────────┐  │
                    │  │ Auth 认证  │  │
                    │  │ WorkOrder │  │
                    │  │ Inventory │  │
                    │  │ Payment   │  │
                    │  │ Report    │  │
                    │  └───────────┘  │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
   │ PostgreSQL  │   │    Redis    │   │ 本地/OSS 存储 │
   │  主数据库    │   │ 缓存/队列/锁 │   │  文件存储    │
   └─────────────┘   └─────────────┘   └─────────────┘
```

---

## 2. 技术选型

### 2.1 选型原则

- **开发效率优先**：小团队快速迭代 MVP
- **生态成熟**：文档完善、社区活跃、人才好招
- **SaaS 友好**：多租户、水平扩展
- **成本可控**：开源为主，云服务按需

### 2.2 技术栈总表

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| **后端语言** | Python | 3.11+ | 开发快、AI 扩展友好 |
| **后端框架** | FastAPI | 0.100+ | 高性能、自动 OpenAPI 文档 |
| **ORM** | SQLAlchemy 2.0 | | 成熟、支持异步 |
| **数据库** | PostgreSQL | 15+ | JSONB、事务可靠、免费 |
| **缓存** | Redis | 7+ | 会话、缓存、分布式锁、队列 |
| **任务队列** | Celery + Redis | | 异步任务（报表、通知） |
| **文件存储** | 本地目录 / 阿里云 OSS | | 开发本地、生产 OSS |
| **PC 前端** | React + TypeScript | 18+ | 生态最大、组件丰富 |
| **UI 框架** | Ant Design | 5.x | 后台管理标准选择 |
| **状态管理** | Zustand / TanStack Query | | 轻量 + 服务端状态 |
| **移动端** | Taro 3 + React | | 一套代码 → H5 + 微信小程序 |
| **构建工具** | Vite | 5+ | 快速 HMR |
| **API 文档** | Swagger (FastAPI 内置) | | 自动生成 |
| **进程管理** | systemd + Gunicorn | | 生产环境，无容器 |
| **CI/CD** | GitHub Actions | | 免费、集成好 |
| **监控** | Sentry + Prometheus | | 错误追踪 + 指标 |

### 2.3 备选方案对比

| 维度 | 方案 A（推荐） | 方案 B | 方案 C |
|------|---------------|--------|--------|
| 后端 | Python + FastAPI | Node.js + NestJS | Go + Gin |
| 前端 | React + Ant Design | Vue 3 + Element Plus | React + shadcn/ui |
| 移动端 | Taro (React) | uni-app (Vue) | React Native |
| 优势 | AI 扩展、开发快 | TS 全栈统一 | 性能最强 |
| 劣势 | 性能略逊 Go | Vue 生态 AI 弱 | 开发速度慢 |

> **推荐方案 A**：Python FastAPI + React + Taro，平衡开发效率与未来 AI 能力扩展。

### 2.4 代码仓库策略（Multi-repo）

前后端使用**独立 Git 仓库**，通过 OpenAPI 契约协作：

| 仓库 | 路径 | 说明 |
|------|------|------|
| **chexiu_bao** | `/Users/zhouli/data/code/chuangye/chexiu_bao` | 后端 API + 产品文档 |
| **chexiu_bao-web** | `/Users/zhouli/data/code/chuangye/chexiu_bao-web` | PC 管理端（二期含 Taro 移动端） |

```
chuangye/
├── chexiu_bao/          # 后端仓库
│   ├── app/             # FastAPI 应用
│   ├── docs/            # PRD、库表、架构（产品文档放后端仓）
│   ├── migrations/
│   └── .env             # 本地配置（PG / Redis 连接）
│
└── chexiu_bao-web/      # 前端仓库
    ├── src/
    ├── .env.development   # VITE_API_BASE_URL=http://localhost:8000
    └── package.json
```

**协作约定：**

| 事项 | 做法 |
|------|------|
| API 契约 | 后端 FastAPI 自动生成 OpenAPI → `http://localhost:8000/openapi.json` |
| 前端类型 | 前端用 `openapi-typescript` 从 OpenAPI 生成 TS 类型 |
| 版本对齐 | 后端发版打 Git tag（如 `v0.1.0`），前端 README 标注兼容版本 |
| 本地联调 | 后端 `uvicorn` 直跑 → 前端 `npm run dev`，Vite 代理或直连 API |
| CI/CD | 各仓库独立流水线，互不影响 |

---

## 3. 后端架构

### 3.1 项目结构

```
chexiu_bao/                     # 后端仓库根目录
├── docs/                       # 产品文档
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置（.env）
│   ├── dependencies.py         # 依赖注入
│   │
│   ├── core/                   # 核心模块
│   │   ├── security.py         # JWT 认证
│   │   ├── permissions.py      # RBAC 权限
│   │   ├── exceptions.py       # 统一异常
│   │   ├── middleware.py       # 中间件（租户、日志）
│   │   └── pagination.py       # 分页
│   │
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── store.py
│   │   ├── user.py
│   │   ├── customer.py
│   │   ├── work_order.py
│   │   ├── inventory.py
│   │   └── payment.py
│   │
│   ├── schemas/                # Pydantic 请求/响应
│   │   ├── store.py
│   │   ├── work_order.py
│   │   └── ...
│   │
│   ├── api/                    # 路由
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── stores.py
│   │   │   ├── customers.py
│   │   │   ├── vehicles.py
│   │   │   ├── work_orders.py
│   │   │   ├── inventory.py
│   │   │   ├── payments.py
│   │   │   └── reports.py
│   │   └── router.py
│   │
│   ├── services/               # 业务逻辑
│   │   ├── work_order_service.py
│   │   ├── inventory_service.py
│   │   ├── payment_service.py
│   │   └── report_service.py
│   │
│   ├── repositories/           # 数据访问层
│   │   └── ...
│   │
│   └── utils/                  # 工具
│       ├── order_no.py         # 单号生成
│       └── storage.py          # 文件上传
│
├── migrations/                 # Alembic 数据库迁移
├── tests/                      # 测试
├── requirements.txt
├── .env.example                # 环境变量模板
├── scripts/
│   ├── dev.sh                  # 本地启动脚本
│   └── deploy.sh               # 生产部署脚本（rsync + systemd reload）
└── README.md
```

### 3.2 分层架构

```
API Layer (路由)
    ↓ 参数校验 (Pydantic Schema)
Service Layer (业务逻辑)
    ↓ 事务管理
Repository Layer (数据访问)
    ↓ SQLAlchemy
Database (PostgreSQL)
```

**职责划分：**

| 层 | 职责 | 禁止 |
|----|------|------|
| API | 路由、参数校验、响应格式化 | 业务逻辑 |
| Service | 业务规则、状态流转、事务 | 直接 SQL |
| Repository | CRUD、查询构建 | 业务判断 |
| Model | 表结构定义 | — |

### 3.3 核心 API 设计

#### 认证

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| GET | `/api/v1/auth/me` | 当前用户信息 |

#### 工单（核心）

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/work-orders` | 接车创建工单 |
| GET | `/api/v1/work-orders` | 工单列表（分页+筛选） |
| GET | `/api/v1/work-orders/{id}` | 工单详情 |
| PUT | `/api/v1/work-orders/{id}/status` | 状态流转 |
| POST | `/api/v1/work-orders/{id}/inspection` | 提交预检/检测 |
| POST | `/api/v1/work-orders/{id}/items` | 添加项目 |
| POST | `/api/v1/work-orders/{id}/parts` | 添加配件 |
| POST | `/api/v1/work-orders/{id}/assign` | 派工 |
| POST | `/api/v1/work-orders/{id}/complete` | 完工 |
| POST | `/api/v1/work-orders/{id}/settle` | 结算 |

#### 库存

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/parts` | 配件列表 |
| POST | `/api/v1/parts` | 新增配件 |
| GET | `/api/v1/inventory` | 库存查询 |
| POST | `/api/v1/inventory/in` | 入库 |
| POST | `/api/v1/inventory/out` | 出库 |
| GET | `/api/v1/inventory/alerts` | 库存预警 |

#### 报表

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/reports/daily` | 营业日报 |
| GET | `/api/v1/reports/revenue-trend` | 营收趋势 |
| GET | `/api/v1/reports/service-analysis` | 项目分析 |

### 3.4 认证与权限

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Login   │ ──→ │  JWT     │ ──→ │  RBAC    │
│  账密/短信 │     │  Token   │     │  权限校验 │
└──────────┘     └──────────┘     └──────────┘
```

- **JWT Access Token**：有效期 2 小时
- **Refresh Token**：有效期 7 天，存 Redis
- **多租户**：Token payload 含 `store_id`，中间件自动注入
- **RBAC 角色**：

| 角色 | 权限范围 |
|------|----------|
| owner | 全部 |
| manager | 除门店设置外全部 |
| receptionist | 接车、开单、收银 |
| technician | 查看派工、更新施工状态 |
| warehouse | 库存管理 |
| finance | 财务报表、结算 |

### 3.5 工单状态机实现

```python
# 伪代码
TRANSITIONS = {
    "pending_inspection": ["pending_check", "cancelled"],
    "pending_check":      ["pending_quote", "cancelled"],
    "pending_quote":      ["pending_confirm", "cancelled"],
    "pending_confirm":    ["in_progress", "cancelled"],
    "in_progress":        ["pending_qc", "cancelled"],
    "pending_qc":         ["pending_settle", "in_progress"],  # 驳回回施工
    "pending_settle":     ["completed"],
}

async def transition(work_order, to_status, operator):
    allowed = TRANSITIONS.get(work_order.status, [])
    if to_status not in allowed:
        raise InvalidTransitionError(...)
    # 更新状态 + 写日志 + 触发副作用（如扣库存）
```

---

## 4. 前端架构

### 4.1 PC Web 管理端

```
chexiu_bao-web/                 # 前端仓库根目录
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes/                  # 路由配置
│   │   └── index.tsx
│   │
│   ├── layouts/                 # 布局
│   │   ├── MainLayout.tsx       # 侧边栏 + 顶栏
│   │   └── AuthLayout.tsx       # 登录页
│   │
│   ├── pages/                   # 页面
│   │   ├── dashboard/           # 首页看板
│   │   ├── work-order/        # 工单管理
│   │   │   ├── List.tsx         # 工单列表
│   │   │   ├── Create.tsx       # 接车开单
│   │   │   ├── Detail.tsx       # 工单详情
│   │   │   └── components/      # 工单子组件
│   │   ├── customer/            # 客户管理
│   │   ├── inventory/           # 库存管理
│   │   ├── service/             # 服务项目
│   │   ├── payment/             # 收银结算
│   │   ├── report/              # 报表
│   │   └── settings/            # 系统设置
│   │
│   ├── components/              # 通用组件
│   │   ├── PlateInput.tsx       # 车牌输入
│   │   ├── CustomerSelect.tsx   # 客户选择器
│   │   ├── PartSelect.tsx       # 配件选择器
│   │   └── StatusTag.tsx        # 状态标签
│   │
│   ├── hooks/                   # 自定义 Hooks
│   ├── services/                # API 调用
│   │   └── api.ts
│   ├── stores/                  # 状态管理
│   │   └── auth.ts
│   ├── types/                   # TypeScript 类型
│   └── utils/                   # 工具函数
│
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### 4.2 页面路由规划

| 路由 | 页面 | 角色 |
|------|------|------|
| `/login` | 登录 | 全部 |
| `/dashboard` | 首页看板 | 全部 |
| `/work-orders` | 工单列表 | 前台+ |
| `/work-orders/create` | 接车开单 | 前台 |
| `/work-orders/:id` | 工单详情 | 全部 |
| `/customers` | 客户列表 | 前台+ |
| `/customers/:id` | 客户详情 | 前台+ |
| `/inventory` | 库存管理 | 仓管+ |
| `/inventory/parts` | 配件档案 | 仓管+ |
| `/services` | 服务项目 | 店长+ |
| `/payments` | 结算记录 | 财务+ |
| `/reports` | 经营报表 | 店长+ |
| `/settings/store` | 门店设置 | 老板 |
| `/settings/users` | 员工管理 | 老板/店长 |

### 4.3 移动端 / 小程序（Taro）

```
mobile/
├── src/
│   ├── app.config.ts            # Taro 路由配置
│   ├── pages/
│   │   ├── index/               # 首页（技师工作台）
│   │   ├── work-order/          # 我的工单
│   │   ├── work-order-detail/   # 工单详情/施工
│   │   ├── checkin/             # 接车（前台）
│   │   └── mine/                # 个人中心
│   │
│   ├── components/
│   ├── services/
│   └── utils/
│
├── project.config.json          # 微信小程序配置
└── package.json
```

**Taro 优势：** 一套 React 代码编译为 H5 + 微信小程序，二期车主端小程序可复用同一技术栈。

---

## 5. 部署架构

> **原则：不使用 Docker。** 本地原生安装依赖，生产环境直部署 + 云托管中间件，构建和发布更快。

### 5.1 开发环境（本地原生）

**依赖安装（macOS）：**

```bash
# PostgreSQL + Redis
brew install postgresql@15 redis

# 启动服务
brew services start postgresql@15
brew services start redis

# 创建数据库
createdb chexiu_bao
```

**后端仓库** — Python 虚拟环境直跑：

```bash
cd chexiu_bao
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 配置 DATABASE_URL、REDIS_URL
alembic upgrade head          # 数据库迁移
uvicorn app.main:app --reload --port 8000
```

**前端仓库** — Vite 开发服务器：

```bash
cd chexiu_bao-web
npm install
npm run dev                     # http://localhost:5173
```

**`.env` 示例（后端）：**

```ini
DATABASE_URL=postgresql://localhost:5432/chexiu_bao
REDIS_URL=redis://localhost:6379/0
STORAGE_TYPE=local              # local | oss
STORAGE_LOCAL_PATH=./uploads    # 开发阶段本地文件存储
SECRET_KEY=dev-secret-key
```

前端 `.env.development`：

```
VITE_API_BASE_URL=http://localhost:8000
```

Vite 代理（避免 CORS）：

```ts
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8000',
  },
},
```

**本地开发最小依赖：**

| 组件 | 开发环境 | 说明 |
|------|----------|------|
| PostgreSQL | Homebrew 本地安装 | 必须 |
| Redis | Homebrew 本地安装 | 必须（会话/缓存） |
| 文件存储 | 本地目录 `./uploads` | MVP 够用，无需 MinIO |
| Python | 3.11+ venv | 必须 |
| Node.js | 18+ | 前端必须 |

### 5.2 生产环境（无 Docker，直部署）

```
                    ┌─────────────┐
                    │   域名/CDN   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx     │
                    │  反向代理+SSL │
                    │  静态文件托管  │
                    └──┬───────┬──┘
                       │       │
              ┌────────▼┐  ┌───▼────────────┐
              │ dist/   │  │ Gunicorn       │
              │ (静态)   │  │ + UvicornWorker│
              └─────────┘  │ (systemd 守护)  │
                           └───┬────────────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
             ┌──────▼──┐ ┌────▼───┐ ┌────▼───┐
             │ RDS PG  │ │云 Redis│ │ OSS   │
             └─────────┘ └────────┘ └────────┘
```

**后端部署流程（`scripts/deploy.sh`）：**

```bash
# 1. 服务器拉代码
git pull origin main

# 2. 安装依赖（仅 requirements.txt，秒级完成）
source .venv/bin/activate && pip install -r requirements.txt

# 3. 数据库迁移
alembic upgrade head

# 4. 重启服务（无镜像构建，秒级生效）
sudo systemctl restart chexiu-bao
```

**Gunicorn systemd 单元（`/etc/systemd/system/chexiu-bao.service`）：**

```ini
[Unit]
Description=ChexiuBao API
After=network.target

[Service]
User=www
WorkingDirectory=/opt/chexiu_bao
EnvironmentFile=/opt/chexiu_bao/.env
ExecStart=/opt/chexiu_bao/.venv/bin/gunicorn app.main:app \
    -w 2 -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**前端部署流程：**

```bash
npm run build          # 本地或 CI 构建，产出 dist/
rsync -avz dist/ user@server:/var/www/chexiu_bao/
# Nginx 直接托管静态文件，无需 Node 进程
```

**对比 Docker 部署的优势：**

| 环节 | Docker | 直部署 |
|------|--------|--------|
| 后端发布 | 构建镜像 1-5 min | `git pull` + `pip install` + restart ≈ 10-30s |
| 前端发布 | 构建镜像 | `npm run build` + rsync ≈ 30s |
| 本地启动 | `docker-compose up` 等镜像 | `uvicorn --reload` 即时 |
| 调试 | 需进容器 | 直接断点调试 |

**推荐云服务（国内）：**

| 组件 | 推荐 | 月费估算 |
|------|------|----------|
| 服务器 | 阿里云 ECS 2C4G | ~100 元 |
| 数据库 | RDS PostgreSQL 基础版 | ~200 元 |
| Redis | 云 Redis 1G | ~100 元 |
| 存储 | OSS 按量 | ~10 元 |
| 域名+SSL | | ~50 元/年 |
| **合计** | | **~400 元/月** |

> PG / Redis 用云托管，不在 ECS 上自己装，运维更省心。

### 5.3 扩展路径（用户增长后）

```
Phase 1 (0-100 店)     单 ECS + systemd + 云 RDS/Redis
Phase 2 (100-1000 店)  后端多实例（Nginx 负载均衡）+ PG 读写分离
Phase 3 (1000+ 店)     微服务拆分 + 分库分表（按需评估是否引入容器）
```

---

## 6. 关键设计决策

### 6.1 多租户方案

| 方案 | 说明 | 选择 |
|------|------|------|
| 独立数据库 | 每门店一个库 | ❌ 成本高 |
| 独立 Schema | 每门店一个 Schema | ❌ 迁移复杂 |
| **共享表 + store_id** | 所有表加 store_id 隔离 | ✅ MVP 首选 |

所有查询强制带 `store_id` 条件，中间件从 JWT 自动注入，防止越权。

### 6.2 文件存储

- 开发：本地目录 `./uploads`（无需 MinIO）
- 生产：阿里云 OSS / 腾讯云 COS
- 代码层抽象 `StorageBackend` 接口，开发用 `LocalStorage`，生产切换 `OSSStorage`
- 图片上传 → 压缩缩略图 → CDN 加速
- 施工照片、预检照片、附件 PDF

### 6.3 实时通知（二期）

- WebSocket 推送：新工单派工、施工完成
- 服务端：FastAPI WebSocket + Redis Pub/Sub
- 客户端：工单详情页实时刷新

### 6.4 打印方案

- 后端生成 PDF（WeasyPrint / ReportLab）
- 前端调用浏览器打印或云打印 API
- 模板：接车单、报价单、结算小票

---

## 7. 安全设计

| 层面 | 措施 |
|------|------|
| 传输 | 全站 HTTPS |
| 认证 | JWT + Refresh Token |
| 密码 | bcrypt 哈希 |
| 权限 | RBAC 角色 + 接口级校验 |
| 租户 | store_id 强制隔离 |
| 输入 | Pydantic 校验 + SQL 参数化 |
| 文件 | 类型/大小限制 + 随机文件名 |
| 日志 | 操作审计 + Sentry 错误追踪 |
| 备份 | PG 每日自动备份 |

---

## 8. 开发规范

### 8.1 Git 分支策略

```
main          ← 生产
  └── develop ← 开发主线
        ├── feature/wo-create    ← 功能分支
        ├── feature/inventory
        └── fix/payment-bug      ← 修复分支
```

### 8.2 代码规范

| 端 | 工具 |
|----|------|
| Python | ruff (lint) + black (format) |
| TypeScript | ESLint + Prettier |
| 提交 | Conventional Commits |

### 8.3 API 规范

- RESTful 风格
- 统一响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

- 分页响应：

```json
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

- 错误码：

| code | 说明 |
|------|------|
| 0 | 成功 |
| 400 | 参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 不存在 |
| 409 | 状态冲突（如非法状态流转） |
| 500 | 服务器错误 |

---

## 9. MVP 开发计划

### 9.1 里程碑

| 阶段 | 时间 | 交付 |
|------|------|------|
| **Sprint 0** | 第 1 周 | 项目脚手架、本地开发环境、CI |
| **Sprint 1** | 第 2-3 周 | 认证、门店、员工、客户/车辆 CRUD |
| **Sprint 2** | 第 4-5 周 | 工单全流程（接车→结算） |
| **Sprint 3** | 第 6-7 周 | 库存管理、派工、施工 |
| **Sprint 4** | 第 8 周 | 报表、打印、联调测试 |
| **Sprint 5** | 第 9 周 | 移动端 H5、Bug 修复、上线 |

### 9.2 Sprint 0 任务清单（下一步）

**后端仓库 `chexiu_bao`：**

- [ ] FastAPI 脚手架 + `.env.example` + 本地启动脚本
- [ ] PostgreSQL + Alembic 初始迁移
- [ ] 登录认证 API + OpenAPI 文档
- [ ] GitHub Actions CI（ruff + pytest）
- [ ] systemd + Gunicorn 部署脚本

**前端仓库 `chexiu_bao-web`：**

- [ ] React + Vite + Ant Design 脚手架
- [ ] 登录页 + API 请求封装（axios + token）
- [ ] OpenAPI 类型生成脚本（`openapi-typescript`）
- [ ] GitHub Actions CI（eslint + build）

---

## 10. 项目目录结构（Multi-repo）

### 10.1 后端仓库 `chexiu_bao`

```
chexiu_bao/
├── docs/                        # 📄 产品文档
│   ├── PRD.md
│   ├── database-schema.md
│   └── architecture.md
├── app/                         # 🐍 FastAPI 应用
│   ├── main.py
│   ├── api/
│   ├── models/
│   ├── services/
│   └── ...
├── migrations/                  # Alembic
├── tests/
├── scripts/
│   ├── dev.sh                   # 本地启动
│   └── deploy.sh                # 生产部署
├── requirements.txt
├── .env.example
├── .github/workflows/ci.yml
└── README.md
```

### 10.2 前端仓库 `chexiu_bao-web`

```
chexiu_bao-web/
├── src/
│   ├── pages/
│   ├── components/
│   ├── services/api.ts
│   └── types/                   # openapi-typescript 生成
├── scripts/
│   └── generate-api-types.sh    # 从后端 OpenAPI 生成类型
├── .env.development
├── .env.production
├── package.json
├── vite.config.ts
├── .github/workflows/ci.yml
└── README.md
```

### 10.3 移动端（二期，可并入前端仓）

Taro 项目建议作为 `chexiu_bao-web/packages/mobile/` 子目录，或独立 `chexiu_bao-mobile` 仓库——二期再定。

---

## 11. 技术风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 单表数据量大（工单） | 查询慢 | 按月分表 / 归档（三期） |
| 并发库存扣减 | 超卖 | Redis 分布式锁 + 乐观锁 |
| 微信支付对接 | 合规复杂 | MVP 先支持现金+手动标记 |
| 车牌 OCR 准确率 | 体验差 | MVP 手动输入，二期接第三方 API |
| 多店扩展 | 架构重构 | 预留 store_id，三期分库 |

---

## 12. 总结

| 维度 | 决策 |
|------|------|
| 代码仓库 | **Multi-repo**（`chexiu_bao` + `chexiu_bao-web`） |
| 架构风格 | 单体后端 + 前后端分离 |
| 部署方式 | **无 Docker**，systemd + Gunicorn + Nginx 静态托管 |
| 后端 | Python FastAPI + SQLAlchemy + PostgreSQL |
| PC 端 | React + TypeScript + Ant Design + Vite |
| 移动端 | Taro 3（H5 + 微信小程序，二期） |
| API 协作 | OpenAPI 契约 + 前端类型自动生成 |
| 中间件 | 云 RDS PostgreSQL + 云 Redis + OSS |
| 多租户 | 共享表 + store_id |
| MVP 周期 | 约 9 周 |

下一步建议：**Sprint 0 — 分别在两个仓库搭建脚手架**。
