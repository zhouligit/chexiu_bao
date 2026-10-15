# 车修宝微信小程序规划

> 版本：v0.1 · 2026-10-08  
> 决策：**先门店端，后车主端**；能力包含 **在线预约** 与 **微信支付**  
> 关联：`PRD.md`、`architecture.md`、`database-schema.md`

---

## 1. 目标与边界

### 1.1 产品目标

| 端 | 用户 | 目标 |
|----|------|------|
| **门店端小程序（优先）** | 老板 / 店长 / 前台 / 技师 / 仓管 | 手机完成日常作业：接车、工单流转、派工施工、预约管理、收款（含微信） |
| **车主端小程序（随后）** | 车主 | 选店预约、查进度、微信支付、评价 |

PC Web（`chexiu_bao-web`）继续承担：复杂开单、库存深度管理、报表、系统设置、订阅套餐。小程序做「高频移动场景」，不做 PC 的 1:1 搬运。

### 1.2 明确不做（本期）

- 会员储值/次卡/优惠券全套营销（可与预约支付解耦，后续迭代）
- 连锁多店总部端
- 技师独立 App（门店端小程序覆盖即可）
- 将 PC 前端直接编译成小程序

---

## 2. 仓库策略（需要新仓库）

### 2.1 结论：**新建独立仓库 `chexiu_bao-mp`**

| 方案 | 结论 |
|------|------|
| 塞进 `chexiu_bao-web` | 不推荐：Vite PC 与微信小程序构建链、依赖、发布节奏完全不同 |
| 后端仓 `chexiu_bao` 内嵌前端 | 不推荐：破坏现有 multi-repo 约定 |
| **新建 `chexiu_bao-mp`** | **推荐**：与 `chexiu_bao` / `chexiu_bao-web` 并列 |

理由：

- 小程序有独立的 `project.config.json`、体验版/正式版发布、审核流程  
- 门店端与车主端可同仓用 Taro **多端/多入口**（或 monorepo packages），避免再拆第四个仓  
- 后端仍只维护一份 API；小程序通过 OpenAPI 协作  

### 2.2 仓库布局（本地）

```
chuangye/
├── chexiu_bao/              # 后端 API + 产品文档（本仓）
├── chexiu_bao-web/          # PC 管理端
└── chexiu_bao-mp/           # 微信小程序（新建）
```

### 2.3 `chexiu_bao-mp` 目录规划

技术选型：**Taro 3 + React + TypeScript**（与现有前端技术栈一致，可编译微信小程序；后续若要 H5 可复用）。

```
chexiu_bao-mp/
├── README.md
├── package.json
├── tsconfig.json
├── project.config.json          # 微信小程序项目配置（appid 等）
├── project.private.config.json  # 本地私有配置（gitignore）
├── config/
│   ├── index.ts                 # Taro 编译配置
│   ├── dev.ts
│   └── prod.ts
├── src/
│   ├── app.ts
│   ├── app.config.ts            # 主包页面路由（按角色可动态，先静态）
│   ├── app.scss
│   ├── types/                   # 与 OpenAPI 对齐的类型
│   ├── services/
│   │   ├── http.ts              # 请求封装（Bearer Token）
│   │   ├── auth.ts
│   │   ├── work-order.ts
│   │   ├── appointment.ts
│   │   └── payment.ts
│   ├── stores/                  # 状态（zustand 等，与 web 可选对齐）
│   ├── utils/
│   │   ├── auth.ts
│   │   └── store-context.ts     # 当前门店上下文
│   │
│   ├── packageStore/            # 分包：门店端（优先开发）
│   │   ├── pages/
│   │   │   ├── home/            # 工作台
│   │   │   ├── work-orders/
│   │   │   ├── work-order-detail/
│   │   │   ├── checkin/         # 接车
│   │   │   ├── appointments/    # 预约列表/确认
│   │   │   ├── payments/        # 收款/退款入口
│   │   │   ├── bind-account/    # 微信绑定员工账号
│   │   │   └── mine/
│   │   └── packageStore.config.ts
│   │
│   └── packageOwner/            # 分包：车主端（二期开发）
│       ├── pages/
│       │   ├── home/
│       │   ├── book/            # 预约下单
│       │   ├── my-orders/
│       │   ├── order-progress/
│       │   ├── pay/
│       │   ├── vehicles/
│       │   └── mine/
│       └── packageOwner.config.ts
│
├── .env.development
├── .env.production
└── scripts/
    └── sync-openapi.sh          # 可选：从后端拉 OpenAPI 生成类型
```

**同一小程序 AppID 下两个分包** 的取舍：

| 方式 | 说明 |
|------|------|
| **推荐：一个小程序 + store/owner 分包** | 一个主体审核；用启动参数 / 码区分入口；共享登录与支付组件 |
| 两个独立小程序 | 审核与类目更清晰，但双倍运营成本；后期再拆也可 |

本期默认：**一个小程序应用，分包隔离门店端/车主端**。

### 2.4 后端仓内配合目录（不新建业务仓）

在现有 `chexiu_bao` 中扩展即可：

```
chexiu_bao/app/
├── api/v1/
│   ├── mp_auth.py               # 小程序登录、绑定
│   ├── appointments.py          # 预约
│   └── ...                      # 现有 work_orders / payments 扩展
├── services/
│   ├── wechat_mp_service.py     # code2session、手机号等
│   ├── wechat_pay_service.py    # JSAPI 下单、回调
│   └── appointment_service.py
├── models/
│   ├── wechat_identity.py       # openid 绑定
│   └── appointment.py
└── migrations/
```

---

## 3. 分期交付计划

### Phase 0 — 基础设施（约 1 周，可与 Phase 1 并行）

| # | 事项 | 产出 |
|---|------|------|
| 0.1 | 微信小程序企业主体、类目、认证 | AppID |
| 0.2 | 配置 request/upload 合法域名 → API 域名 | 可真机调试 |
| 0.3 | 开通微信支付商户号，绑定小程序，门店进件策略 | 可调支付沙箱/正式 |
| 0.4 | 创建 Git 仓库 `chexiu_bao-mp`，Taro 脚手架 | 空工程可编译 |
| 0.5 | 后端配置：`WECHAT_MP_APPID/SECRET`、支付商户密钥 | `.env.example` 更新 |

### Phase 1 — 门店端 MVP（约 3～5 周）

**目标：** 员工微信登录并干活；能管预约；能对工单发起/确认微信支付收款。

| # | 事项 | 说明 |
|---|------|------|
| 1.1 | 员工微信登录 | `wx.login` → `code2session`；首次用账号密码绑定 `user_id`↔`openid` |
| 1.2 | 工作台首页 | 待办：待接车/施工中/待结算/今日预约 |
| 1.3 | 工单列表 + 详情 | 复用现有状态机；大按钮流转；拍照上传走现有 uploads |
| 1.4 | 简易接车 | 车牌 + 选客户/建档 → 创建工单 |
| 1.5 | 技师视角 | 「我的任务」、开工/完工 |
| 1.6 | 预约管理（门店侧） | 日历/列表、确认、改期、到店转工单、取消 |
| 1.7 | 微信支付（门店收款） | 工单结算选「微信」→ 生成收款码/JSAPI（顾客扫或顾客端付） |
| 1.8 | 订阅校验 | 复用现有 `require_writable_subscription`；过期只读提示 |

**门店端 MVP 验收：**

- [ ] 技师手机完成：看单 → 施工状态 → 传图  
- [ ] 前台手机完成：接车建单、确认预约到店  
- [ ] 结算走通微信支付并写入现有收款流水  

### Phase 2 — 车主端 MVP（约 3～4 周，Phase 1 后）

| # | 事项 | 说明 |
|---|------|------|
| 2.1 | 车主登录 | 微信登录 + 手机号；绑定客户档案 |
| 2.2 | 进店上下文 | 门店太阳码 / 短链带 `store_id` |
| 2.3 | 在线预约 | 选服务、选时间段、留车牌/诉求 → 创建预约单 |
| 2.4 | 我的工单 / 进度 | 只读状态时间线 |
| 2.5 | 微信支付（车主付） | 预约定金或工单尾款 JSAPI |
| 2.6 | 评价（可选） | 完工后简单评分 |

**车主端 MVP 验收：**

- [ ] 扫门店码 → 预约成功 → 门店端可见  
- [ ] 进行中工单可查进度  
- [ ] 车主完成一笔微信支付  

### Phase 3 — 增强（持续）

- 预约时段库存/技师容量、提醒订阅消息  
- 退款原路退回、分账（若多门店）  
- 会员卡抵扣与预约结合  
- 门店端补库存盘点等低频能力  

---

## 4. 关键业务设计（摘要）

### 4.1 预约 `appointment`

建议新表（详细字段落入 `database-schema.md` 后续迁移时补全）：

| 字段要点 | 说明 |
|----------|------|
| store_id | 门店 |
| customer_id / vehicle_id | 可空（车主未建档时用快照字段） |
| service_item_ids / 备注 | 意向项目 |
| scheduled_start / end | 预约时段 |
| status | pending / confirmed / arrived / cancelled / expired / converted |
| source | mp_owner / mp_store / phone |
| work_order_id | 到店转工单后关联 |
| pay_status / deposit_amount | 若收预约金 |

门店端：确认/改期/取消/一键转工单。  
车主端：提交预约、取消（规则内）、查看状态。

### 4.2 微信支付

| 场景 | 付款人 | 方式 |
|------|--------|------|
| 门店收银 | 车主 | 门店小程序调起支付 或 展示收款码（Native/JSAPI 按产品选） |
| 车主端支付 | 车主 | 车主小程序 JSAPI |

实现要点：

- 统一 `payment` 流水表扩展：`channel=wechat`、`transaction_id`、`openid`  
- 回调地址：`/api/v1/payments/wechat/notify`（验签、幂等）  
- 支付成功 → 更新工单结算状态 / 预约金状态  
- 与现有现金/微信「手工记账」并存：小程序走自动回调，PC 仍可手工登记  

### 4.3 身份模型

| 表/概念 | 说明 |
|---------|------|
| `wechat_user` 或绑定表 | openid、unionid、appid |
| 员工绑定 | openid → user_id（门店端） |
| 车主绑定 | openid → customer_id（可多门店：openid+store_id） |

---

## 5. API 规划（后端新增/扩展）

前缀建议：

```
/api/v1/mp/auth/*           # 登录、绑定、换 token
/api/v1/appointments/*      # 预约 CRUD + 状态
/api/v1/payments/wechat/*   # 预下单、回调
```

门店端继续使用现有：

```
/api/v1/work-orders/*
/api/v1/customers/*
/api/v1/uploads/*
```

鉴权：小程序 Token 与 PC 共用 JWT 体系，claim 中增加 `client=mp_store|mp_owner`。  
写操作继续走订阅 `can_write` 校验。

---

## 6. 风险与依赖

| 风险 | 应对 |
|------|------|
| 小程序类目/资质审核 | Phase 0 尽早提交；汽车服务相关资质提前准备 |
| 支付进件周期长 | 与门店端 UI 并行，先用模拟支付/沙箱联调 |
| 一个小程序双端入口混淆 | 启动页根据绑定身份跳转 store/owner 分包；未绑定先选角色 |
| 订阅过期 | 门店端提示续费（可跳 PC 或客服）；车主端只读历史 |

---

## 7. 近期行动清单（可执行）

> 更新：2026-10-08。仓库暂不合仓；PC 预约管理暂不做，等小程序预约跑稳、出现坐席/看板需求再补轻量页。

### 7.1 已完成（开发侧）

- [x] 独立仓 `chexiu_bao-mp`：Taro 4 + 门店/车主分包脚手架，`build:weapp` 可通过  
- [x] 后端 `WECHAT_MP_APP_ID` / `WECHAT_MP_APP_SECRET`（未配置走 mock openid）  
- [x] `wechat_identity`（迁移 `007`）+ `/api/v1/mp/auth/login|bind|me`  
- [x] `appointment`（迁移 `008`）+ `/api/v1/appointments`（列表/新建/确认/到店/取消/转工单）  
- [x] 门店小程序：登录绑定、预约列表/新建/详情  

### 7.2 你现在要做的（联调与账号）

勾选清单：

1. [ ] 迁移库表到 `008`  
2. [ ] 启动后端，确认健康检查与 PC 登录  
3. [ ] 微信开发者工具打开小程序工程  
4. [ ] 开发期关闭域名校验  
5. [ ] 模拟器走通：登录 → 绑定 → 预约  
6. [ ] 注册小程序，拿到 AppID / AppSecret  
7. [ ] 后端 `.env` 配置微信凭据（AppID 已备好；生产机仍需写 `WECHAT_MP_APP_ID` + `SECRET`）  
8. [x] 替换小程序 `project.config.json` 的 appid（`wxeeac56d862611875`）  
9. [ ] 公众平台配置 request 合法域名  
10. [ ] （可稍后）开通微信支付  

**操作步骤见下方 §7.5。**

### 7.3 接下来开发（需开工时再说）

门店端 MVP 剩余，建议顺序：

1. [x] 工作台待办（今日预约 / 待预检 / 施工中 / 待结算）  
2. [x] 工单列表 + 状态流转（拍照上传稍后）  
3. [x] 简易接车开单  
4. 微信支付（门店收款）  
5. 车主端预约/支付（Phase 2，门店端稳定后再开）  

### 7.4 明确暂不做

- `chexiu_bao-web` 与 `chexiu_bao-mp` 合仓  
- PC 端预约管理页  
- 车主端完整页面、会员营销、技师独立 App

### 7.5 十条待办的具体操作步骤

约定路径（按你本机调整）：

| 角色 | 路径 |
|------|------|
| 后端仓 | `/Users/zhouli/data/code/chuangye/chexiu_bao` |
| 小程序仓 | `/Users/zhouli/data/code/chuangye/chexiu_bao-mp` |
| 生产 API | `https://chexiu-api.yikuaikaixin.cn`（与 mp `.env.production` 一致） |
| 本地 API | `http://127.0.0.1:8000`（mp `.env.development`） |

---

#### 步骤 1 — 执行数据库迁移（到 `008`）

**本地：**

```bash
cd /Users/zhouli/data/code/chuangye/chexiu_bao
source .venv/bin/activate
# 确认 .env 里 DATABASE_URL 指向你要升级的库
alembic upgrade head
alembic current   # 期望显示 008（或含 008 的 revision）
```

**生产服务器：** SSH 登录后进入后端部署目录，同样 `source` 虚拟环境 → `alembic upgrade head`。  
MySQL / PostgreSQL 均可，只要 `DATABASE_URL` 正确。

---

#### 步骤 2 — 启动后端并自检

```bash
cd /Users/zhouli/data/code/chuangye/chexiu_bao
source .venv/bin/activate
./scripts/dev.sh
# 或：uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

浏览器或 curl：

1. `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`  
2. PC 打开管理端，用 `admin` / `admin123`（或你的账号）登录成功  
3. 可选：打开 `http://127.0.0.1:8000/docs`，能看到 `/api/v1/mp/auth/*`、`/api/v1/appointments`  

生产环境则访问 `https://chexiu-api.yikuaikaixin.cn/health`。

---

#### 步骤 3 — 微信开发者工具打开工程

1. 安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)  
2. 本机编译小程序：

```bash
cd /Users/zhouli/data/code/chuangye/chexiu_bao-mp
npm install --registry=https://registry.npmjs.org/
npm run dev:weapp
```

3. 开发者工具 → **导入项目**  
   - 目录：选 **`chexiu_bao-mp` 仓根**（不是 `dist/`；`project.config.json` 里已写 `miniprogramRoot: dist/`）  
   - AppID：暂无正式号时选「测试号 / 游客」或填 `touristappid`  
4. 等 watch 编译完成后，模拟器应出现「车修宝」启动页  

若白屏：看工具「调试器」Console；确认 `dist/app.json` 已生成。

---

#### 步骤 4 — 开发期关闭域名校验

开发者工具顶部菜单：

**详情 → 本地设置 → 勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」**

本地连 `http://127.0.0.1:8000` 必须勾上。真机预览连生产 HTTPS 且域名已备案配置后，再关掉此勾选做验收。

---

#### 步骤 5 — 模拟器走通主流程

前提：步骤 1～4 完成；后端未配微信时走 **mock openid**（正常）。

1. 模拟器打开小程序 → 自动调登录；未绑定会进「绑定门店账号」  
2. 输入 PC 已有账号（如 `admin` / `admin123`）→ 绑定成功 → 进门店工作台  
3. **预约管理** → **新建**：填联系人、手机、车牌、时间 → 创建  
4. 进详情：**确认预约** → **标记到店** → **转工单**（需有车牌）  
5. 列表 Tab「待确认 / 已确认 / 已到店 / 全部」能切换看到数据  

若报「未登录 / 请求失败」：确认开发者工具网络面板请求打到 `TARO_APP_API_BASE`，且后端 CORS/服务在跑。

---

#### 步骤 6 — 注册小程序，拿到 AppID / AppSecret

1. 打开 [微信公众平台](https://mp.weixin.qq.com/) → 注册 → 选择 **小程序**  
2. 主体：优先 **企业**（个体工商户也可；个人主体类目受限，汽车服务相关可能过不了）  
3. 完成管理员微信扫码、邮箱、主体证件等认证（企业认证通常需付费年审）  
4. 登录小程序后台 → **设置 → 基本设置**：复制 **AppID(小程序ID)**  
5. 同页或 **开发管理 → 开发设置**：生成并妥善保存 **AppSecret**（只显示一次，丢失需重置）  
6. **设置 → 基本设置 → 服务类目**：选与汽修/汽车服务相符的类目（按微信当前类目表填写，可能要资质）  

把 AppID、AppSecret 存到密码管理器，**不要提交到 Git**。

---

#### 步骤 7 — 后端写入微信凭据

在**实际运行后端的那台机器**的 `.env`（不要用 `.env.example` 当生产文件）增加：

```env
WECHAT_MP_APP_ID=wx开头的AppID
WECHAT_MP_APP_SECRET=你的AppSecret
```

然后**重启**后端进程（systemd / 开发 uvicorn 均可）。

验证方式：配好后，小程序真机 `wx.login` 的 code 可换到真实 openid；日志里不应再出现 `WECHAT_MP mock code2session`。

---

#### 步骤 8 — 替换小程序工程里的 appid

编辑 `chexiu_bao-mp/project.config.json`：

```json
"appid": "wx你的正式AppID"
```

保存后，用开发者工具重新打开/编译；详情里应显示正式 AppID。  
同时确认 `.env.production` 里 `TARO_APP_API_BASE=https://chexiu-api.yikuaikaixin.cn`（或你的正式 API）。

---

#### 步骤 9 — 配置 request 合法域名（真机必做）

1. 登录 [mp.weixin.qq.com](https://mp.weixin.qq.com/) → 你的小程序  
2. **开发管理 → 开发设置 → 服务器域名**  
3. **request 合法域名** 点击修改，添加（**不要带路径、不要带端口、必须 https**）：

   ```text
   https://chexiu-api.yikuaikaixin.cn
   ```

4. 若小程序要上传图片到同一 API 域名下的上传接口，把同一域名也加到 **uploadFile 合法域名**  
5. 保存（每月修改次数有限，一次改准）  

**域名要求：** 已备案（国内）、HTTPS 证书有效、ICP 与主体匹配（按微信当时规则）。  
真机预览：开发者工具点「预览」→ 手机扫码；此时应**取消**勾选「不校验合法域名」做最终验收。

本地继续用模拟器 + 不校验域名 + `127.0.0.1` 即可，与真机配置不冲突。

---

#### 步骤 10 —（可延后）微信支付商户号

做到「工单微信收款 / 车主支付」前再做即可：

1. 在 [微信支付商户平台](https://pay.weixin.qq.com/) 注册商户号  
2. 商户号与小程序 AppID **绑定关联**  
3. 拿到商户号、APIv3 密钥、证书等，再写入后端支付相关配置（届时再补 `.env` 项与代码）  
4. 多门店进件/分账策略按业务另定  

**当前预约与登录不依赖支付**，可全部勾完 1～9 后再做本步。

---

## 8. 文档维护

| 文档 | 职责 |
|------|------|
| **本文件** `mini-program-plan.md` | 小程序范围、分期、仓库与目录 |
| `PRD.md` | 阶段划分与功能条目同步 |
| `architecture.md` | 三仓布局与 Taro 位置 |
| `database-schema.md` | 预约/微信/支付字段（实现前补齐） |

变更流程：产品范围变动先改本文件与 PRD，再开任务开发。
