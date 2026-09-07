# 车修宝 API 后端

汽车门店管理系统后端服务（FastAPI + PostgreSQL）。

## 快速开始

```bash
# 1. 安装依赖（PostgreSQL 需已启动并创建数据库）
createdb chexiu_bao

# 2. 配置环境
cp .env.example .env

# 3. 启动开发服务
chmod +x scripts/dev.sh
./scripts/dev.sh
```

API 文档：http://localhost:8000/docs

## 默认账号

| 用户名 | 密码 |
|--------|------|
| admin | admin123 |

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| GET | `/api/v1/auth/me` | 当前用户 |
| GET | `/api/v1/customers` | 客户列表 |
| POST | `/api/v1/customers` | 创建客户 |
| GET | `/api/v1/work-orders` | 工单列表 |
| POST | `/api/v1/work-orders` | 接车开单 |
| GET | `/api/v1/work-orders/{id}` | 工单详情 |
| PUT | `/api/v1/work-orders/{id}/status` | 状态流转 |
| POST | `/api/v1/work-orders/{id}/items` | 添加项目 |
| POST | `/api/v1/work-orders/{id}/parts` | 添加配件 |
| POST | `/api/v1/work-orders/{id}/settle` | 收银结算 |
| GET | `/api/v1/service-items` | 服务项目列表 |
| GET | `/api/v1/parts` | 配件列表（含库存） |
| POST | `/api/v1/parts` | 新增配件 |
| POST | `/api/v1/inventory/in` | 入库 |
| GET | `/api/v1/inventory/alerts` | 库存预警 |
| GET | `/api/v1/reports/overview` | 经营概览（首页） |
| GET | `/api/v1/reports/daily` | 营业日报 |
| GET | `/api/v1/reports/revenue-trend` | 营收趋势 |
| GET | `/api/v1/reports/service-analysis` | 项目分析 |

## 生产部署

```bash
./scripts/deploy.sh
```

使用 systemd + Gunicorn，详见 `docs/architecture.md`。

## 测试

```bash
source .venv/bin/activate
pytest
```
