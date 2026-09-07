# 车修宝（ChexiuBao）数据库设计

> 版本：v0.1 · 2026-09-07  
> 数据库：PostgreSQL 15+  
> 字符集：UTF-8

---

## 1. 设计原则

| 原则 | 说明 |
|------|------|
| **多租户隔离** | 所有业务表含 `store_id`，SaaS 按门店隔离 |
| **软删除** | 核心表用 `deleted_at` 软删除，保留审计 |
| **统一审计字段** | `created_at`、`updated_at`、`created_by`、`updated_by` |
| **金额精度** | 金额用 `DECIMAL(12,2)`，避免浮点误差 |
| **状态机** | 工单等核心实体用 `status` 枚举字段 |
| **外键策略** | 逻辑外键为主（应用层约束），减少锁竞争 |

---

## 2. ER 关系概览

```
store (门店)
  ├── user (员工)
  ├── customer (客户)
  │     └── vehicle (车辆)
  ├── service_item (服务项目)
  ├── part (配件)
  │     └── inventory (库存)
  ├── supplier (供应商)
  └── work_order (工单) ──核心──
        ├── work_order_inspection (预检/检测)
        ├── work_order_item (项目明细)
        ├── work_order_part (配件明细)
        ├── work_order_assignment (派工)
        ├── work_order_log (状态日志)
        └── payment (结算/支付)

── 二期 ──
  ├── member_card (会员卡)
  ├── coupon (优惠券)
  └── commission (提成)
```

---

## 3. 表结构详述

### 3.1 系统与组织

#### `store` — 门店

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| name | VARCHAR(100) | NOT NULL | 门店名称 |
| code | VARCHAR(32) | UNIQUE | 门店编码 |
| phone | VARCHAR(20) | | 联系电话 |
| address | VARCHAR(255) | | 地址 |
| logo_url | VARCHAR(500) | | Logo |
| business_hours | JSONB | | 营业时间 `{"mon":"08:00-18:00",...}` |
| status | SMALLINT | DEFAULT 1 | 1=正常 0=停用 |
| plan | VARCHAR(20) | DEFAULT 'basic' | 套餐版本 |
| expired_at | TIMESTAMP | | 订阅到期时间 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |
| deleted_at | TIMESTAMP | | 软删除 |

```sql
CREATE TABLE store (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    code        VARCHAR(32) UNIQUE,
    phone       VARCHAR(20),
    address     VARCHAR(255),
    logo_url    VARCHAR(500),
    business_hours JSONB,
    status      SMALLINT DEFAULT 1,
    plan        VARCHAR(20) DEFAULT 'basic',
    expired_at  TIMESTAMP,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMP
);
CREATE INDEX idx_store_code ON store(code) WHERE deleted_at IS NULL;
```

#### `work_bay` — 工位

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | |
| store_id | BIGINT | NOT NULL | 所属门店 |
| name | VARCHAR(50) | NOT NULL | 工位名称，如"1号工位" |
| type | VARCHAR(20) | | 类型：repair/wash/beauty |
| status | SMALLINT | DEFAULT 1 | 1=空闲 2=占用 0=停用 |
| sort_order | INT | DEFAULT 0 | 排序 |

```sql
CREATE TABLE work_bay (
    id          BIGSERIAL PRIMARY KEY,
    store_id    BIGINT NOT NULL,
    name        VARCHAR(50) NOT NULL,
    type        VARCHAR(20),
    status      SMALLINT DEFAULT 1,
    sort_order  INT DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_work_bay_store ON work_bay(store_id);
```

#### `user` — 员工

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | |
| store_id | BIGINT | NOT NULL | 所属门店 |
| username | VARCHAR(50) | NOT NULL | 登录名 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| phone | VARCHAR(20) | | 手机 |
| role | VARCHAR(20) | NOT NULL | owner/manager/receptionist/technician/warehouse/finance |
| avatar_url | VARCHAR(500) | | 头像 |
| status | SMALLINT | DEFAULT 1 | 1=正常 0=禁用 |
| last_login_at | TIMESTAMP | | 最后登录 |

```sql
CREATE TABLE "user" (
    id              BIGSERIAL PRIMARY KEY,
    store_id        BIGINT NOT NULL,
    username        VARCHAR(50) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(50) NOT NULL,
    phone           VARCHAR(20),
    role            VARCHAR(20) NOT NULL,
    avatar_url      VARCHAR(500),
    status          SMALLINT DEFAULT 1,
    last_login_at   TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMP,
    UNIQUE(store_id, username)
);
CREATE INDEX idx_user_store ON "user"(store_id);
CREATE INDEX idx_user_phone ON "user"(phone);
```

#### `operation_log` — 操作日志（二期）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | 门店 |
| user_id | BIGINT | 操作人 |
| action | VARCHAR(50) | 操作类型 |
| target_type | VARCHAR(50) | 对象类型 |
| target_id | BIGINT | 对象 ID |
| detail | JSONB | 变更详情 |
| ip | VARCHAR(45) | IP 地址 |
| created_at | TIMESTAMP | |

---

### 3.2 客户与车辆

#### `customer` — 客户

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | |
| store_id | BIGINT | NOT NULL | |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| phone | VARCHAR(20) | NOT NULL | 手机（门店内唯一） |
| gender | SMALLINT | | 0=未知 1=男 2=女 |
| source | VARCHAR(30) | | 来源：walk_in/referral/online/ad |
| remark | TEXT | | 备注 |
| tags | JSONB | | 标签数组 `["VIP","流失预警"]` |
| total_spent | DECIMAL(12,2) | DEFAULT 0 | 累计消费 |
| visit_count | INT | DEFAULT 0 | 到店次数 |
| last_visit_at | TIMESTAMP | | 最后到店 |

```sql
CREATE TABLE customer (
    id              BIGSERIAL PRIMARY KEY,
    store_id        BIGINT NOT NULL,
    name            VARCHAR(50) NOT NULL,
    phone           VARCHAR(20) NOT NULL,
    gender          SMALLINT,
    source          VARCHAR(30),
    remark          TEXT,
    tags            JSONB DEFAULT '[]',
    total_spent     DECIMAL(12,2) DEFAULT 0,
    visit_count     INT DEFAULT 0,
    last_visit_at   TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMP,
    UNIQUE(store_id, phone)
);
CREATE INDEX idx_customer_store ON customer(store_id);
CREATE INDEX idx_customer_phone ON customer(store_id, phone);
CREATE INDEX idx_customer_name ON customer(store_id, name);
```

#### `vehicle` — 车辆

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | |
| store_id | BIGINT | NOT NULL | |
| customer_id | BIGINT | NOT NULL | 所属客户 |
| plate_number | VARCHAR(20) | NOT NULL | 车牌号 |
| vin | VARCHAR(17) | | 车架号 |
| brand | VARCHAR(50) | | 品牌 |
| series | VARCHAR(50) | | 车系 |
| model | VARCHAR(100) | | 车型 |
| year | SMALLINT | | 年款 |
| color | VARCHAR(20) | | 颜色 |
| mileage | INT | | 当前里程(km) |
| engine_no | VARCHAR(50) | | 发动机号 |
| remark | TEXT | | 备注 |

```sql
CREATE TABLE vehicle (
    id              BIGSERIAL PRIMARY KEY,
    store_id        BIGINT NOT NULL,
    customer_id     BIGINT NOT NULL,
    plate_number    VARCHAR(20) NOT NULL,
    vin             VARCHAR(17),
    brand           VARCHAR(50),
    series          VARCHAR(50),
    model           VARCHAR(100),
    year            SMALLINT,
    color           VARCHAR(20),
    mileage         INT,
    engine_no       VARCHAR(50),
    remark          TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMP,
    UNIQUE(store_id, plate_number)
);
CREATE INDEX idx_vehicle_customer ON vehicle(customer_id);
CREATE INDEX idx_vehicle_plate ON vehicle(store_id, plate_number);
CREATE INDEX idx_vehicle_vin ON vehicle(vin);
```

---

### 3.3 服务项目

#### `service_category` — 项目分类

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | 门店（0=系统预设） |
| name | VARCHAR(50) | 分类名：维修/保养/洗美/轮胎 |
| sort_order | INT | 排序 |

#### `service_item` — 服务项目

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | |
| store_id | BIGINT | NOT NULL | |
| category_id | BIGINT | | 分类 |
| name | VARCHAR(100) | NOT NULL | 项目名称 |
| code | VARCHAR(32) | | 项目编码 |
| price | DECIMAL(10,2) | NOT NULL | 标准售价 |
| cost_price | DECIMAL(10,2) | | 成本价 |
| labor_hours | DECIMAL(5,2) | | 标准工时 |
| labor_price | DECIMAL(10,2) | | 工时单价 |
| unit | VARCHAR(10) | DEFAULT '次' | 单位 |
| description | TEXT | | 描述 |
| status | SMALLINT | DEFAULT 1 | 1=启用 0=停用 |

```sql
CREATE TABLE service_item (
    id              BIGSERIAL PRIMARY KEY,
    store_id        BIGINT NOT NULL,
    category_id     BIGINT,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(32),
    price           DECIMAL(10,2) NOT NULL,
    cost_price      DECIMAL(10,2),
    labor_hours     DECIMAL(5,2),
    labor_price     DECIMAL(10,2),
    unit            VARCHAR(10) DEFAULT '次',
    description     TEXT,
    status          SMALLINT DEFAULT 1,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMP
);
CREATE INDEX idx_service_item_store ON service_item(store_id);
```

---

### 3.4 配件与库存

#### `part_category` — 配件分类

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | |
| name | VARCHAR(50) | 分类名 |
| parent_id | BIGINT | 父分类 |

#### `part` — 配件档案

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | |
| store_id | BIGINT | NOT NULL | |
| category_id | BIGINT | | 分类 |
| name | VARCHAR(100) | NOT NULL | 配件名称 |
| code | VARCHAR(32) | | 配件编码/SKU |
| brand | VARCHAR(50) | | 品牌 |
| spec | VARCHAR(100) | | 规格型号 |
| unit | VARCHAR(10) | DEFAULT '个' | 单位 |
| purchase_price | DECIMAL(10,2) | | 采购价 |
| sell_price | DECIMAL(10,2) | | 销售价 |
| safe_stock | INT | DEFAULT 0 | 安全库存 |
| status | SMALLINT | DEFAULT 1 | |

```sql
CREATE TABLE part (
    id              BIGSERIAL PRIMARY KEY,
    store_id        BIGINT NOT NULL,
    category_id     BIGINT,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(32),
    brand           VARCHAR(50),
    spec            VARCHAR(100),
    unit            VARCHAR(10) DEFAULT '个',
    purchase_price  DECIMAL(10,2),
    sell_price      DECIMAL(10,2),
    safe_stock      INT DEFAULT 0,
    status          SMALLINT DEFAULT 1,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMP,
    UNIQUE(store_id, code)
);
CREATE INDEX idx_part_store ON part(store_id);
CREATE INDEX idx_part_code ON part(store_id, code);
```

#### `inventory` — 库存

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | |
| store_id | BIGINT | NOT NULL | |
| part_id | BIGINT | NOT NULL | 配件 |
| quantity | INT | NOT NULL DEFAULT 0 | 当前库存 |
| locked_quantity | INT | DEFAULT 0 | 锁定数量（工单占用） |
| avg_cost | DECIMAL(10,2) | | 加权平均成本 |
| warehouse_location | VARCHAR(50) | | 库位 |

```sql
CREATE TABLE inventory (
    id                  BIGSERIAL PRIMARY KEY,
    store_id            BIGINT NOT NULL,
    part_id             BIGINT NOT NULL,
    quantity            INT NOT NULL DEFAULT 0,
    locked_quantity     INT DEFAULT 0,
    avg_cost            DECIMAL(10,2),
    warehouse_location  VARCHAR(50),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(store_id, part_id)
);
CREATE INDEX idx_inventory_store ON inventory(store_id);
```

#### `inventory_log` — 库存流水

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | |
| part_id | BIGINT | |
| type | VARCHAR(20) | in/out/lock/unlock/adjust |
| quantity | INT | 变动数量（正=入，负=出） |
| before_qty | INT | 变动前 |
| after_qty | INT | 变动后 |
| ref_type | VARCHAR(30) | 关联类型：work_order/purchase/adjust |
| ref_id | BIGINT | 关联 ID |
| remark | VARCHAR(255) | |
| operator_id | BIGINT | 操作人 |
| created_at | TIMESTAMP | |

```sql
CREATE TABLE inventory_log (
    id          BIGSERIAL PRIMARY KEY,
    store_id    BIGINT NOT NULL,
    part_id     BIGINT NOT NULL,
    type        VARCHAR(20) NOT NULL,
    quantity    INT NOT NULL,
    before_qty  INT NOT NULL,
    after_qty   INT NOT NULL,
    ref_type    VARCHAR(30),
    ref_id      BIGINT,
    remark      VARCHAR(255),
    operator_id BIGINT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_inv_log_part ON inventory_log(store_id, part_id);
CREATE INDEX idx_inv_log_ref ON inventory_log(ref_type, ref_id);
```

#### `supplier` — 供应商

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | |
| name | VARCHAR(100) | 供应商名称 |
| contact | VARCHAR(50) | 联系人 |
| phone | VARCHAR(20) | 电话 |
| address | VARCHAR(255) | 地址 |
| remark | TEXT | |

---

### 3.5 工单（核心）

#### `work_order` — 工单

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | |
| store_id | BIGINT | NOT NULL | |
| order_no | VARCHAR(32) | UNIQUE | 工单号 WO202609070001 |
| customer_id | BIGINT | NOT NULL | 客户 |
| vehicle_id | BIGINT | NOT NULL | 车辆 |
| status | VARCHAR(20) | NOT NULL | 状态枚举（见下） |
| mileage_in | INT | | 进店里程 |
| fuel_level | VARCHAR(10) | | 油量 |
| customer_request | TEXT | | 客户诉求 |
| internal_note | TEXT | | 内部备注 |
| receptionist_id | BIGINT | | 接车顾问 |
| total_amount | DECIMAL(12,2) | DEFAULT 0 | 项目+配件合计 |
| discount_amount | DECIMAL(12,2) | DEFAULT 0 | 折扣金额 |
| payable_amount | DECIMAL(12,2) | DEFAULT 0 | 应付金额 |
| paid_amount | DECIMAL(12,2) | DEFAULT 0 | 已付金额 |
| estimated_finish_at | TIMESTAMP | | 预计完工 |
| finished_at | TIMESTAMP | | 实际完工 |
| settled_at | TIMESTAMP | | 结算时间 |

**status 枚举：**

| 值 | 说明 |
|----|------|
| `pending_inspection` | 待预检 |
| `pending_check` | 待检测 |
| `pending_quote` | 待报价 |
| `pending_confirm` | 待客户确认 |
| `in_progress` | 施工中 |
| `pending_qc` | 待质检 |
| `pending_settle` | 待结算 |
| `completed` | 已完成 |
| `cancelled` | 已取消 |

```sql
CREATE TABLE work_order (
    id                  BIGSERIAL PRIMARY KEY,
    store_id            BIGINT NOT NULL,
    order_no            VARCHAR(32) NOT NULL UNIQUE,
    customer_id         BIGINT NOT NULL,
    vehicle_id          BIGINT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending_inspection',
    mileage_in          INT,
    fuel_level          VARCHAR(10),
    customer_request    TEXT,
    internal_note       TEXT,
    receptionist_id     BIGINT,
    total_amount        DECIMAL(12,2) DEFAULT 0,
    discount_amount     DECIMAL(12,2) DEFAULT 0,
    payable_amount      DECIMAL(12,2) DEFAULT 0,
    paid_amount         DECIMAL(12,2) DEFAULT 0,
    estimated_finish_at TIMESTAMP,
    finished_at         TIMESTAMP,
    settled_at          TIMESTAMP,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMP
);
CREATE INDEX idx_wo_store ON work_order(store_id);
CREATE INDEX idx_wo_status ON work_order(store_id, status);
CREATE INDEX idx_wo_customer ON work_order(customer_id);
CREATE INDEX idx_wo_vehicle ON work_order(vehicle_id);
CREATE INDEX idx_wo_created ON work_order(store_id, created_at DESC);
CREATE INDEX idx_wo_order_no ON work_order(order_no);
```

#### `work_order_inspection` — 预检/检测

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| work_order_id | BIGINT | 工单 |
| type | VARCHAR(20) | pre_check/check（预检/检测） |
| items | JSONB | 检测项 `[{"name":"左前轮胎","status":"normal","note":""}]` |
| photos | JSONB | 照片 URL 数组 |
| valuables | TEXT | 贵重物品清单 |
| inspector_id | BIGINT | 检测人 |
| created_at | TIMESTAMP | |

```sql
CREATE TABLE work_order_inspection (
    id              BIGSERIAL PRIMARY KEY,
    work_order_id   BIGINT NOT NULL,
    type            VARCHAR(20) NOT NULL,
    items           JSONB,
    photos          JSONB DEFAULT '[]',
    valuables       TEXT,
    inspector_id    BIGINT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_wo_inspection ON work_order_inspection(work_order_id);
```

#### `work_order_item` — 工单项目明细

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| work_order_id | BIGINT | |
| service_item_id | BIGINT | 关联服务项目（可为空=自定义） |
| name | VARCHAR(100) | 项目名称 |
| quantity | DECIMAL(8,2) | 数量 |
| unit_price | DECIMAL(10,2) | 单价 |
| discount | DECIMAL(5,2) | 折扣(0-100) |
| amount | DECIMAL(10,2) | 小计 |
| labor_hours | DECIMAL(5,2) | 工时 |
| type | VARCHAR(20) | normal/addon（正常/增项） |
| status | VARCHAR(20) | pending/in_progress/completed |
| technician_id | BIGINT | 施工技师 |

```sql
CREATE TABLE work_order_item (
    id              BIGSERIAL PRIMARY KEY,
    work_order_id   BIGINT NOT NULL,
    service_item_id BIGINT,
    name            VARCHAR(100) NOT NULL,
    quantity        DECIMAL(8,2) DEFAULT 1,
    unit_price      DECIMAL(10,2) NOT NULL,
    discount        DECIMAL(5,2) DEFAULT 100,
    amount          DECIMAL(10,2) NOT NULL,
    labor_hours     DECIMAL(5,2),
    type            VARCHAR(20) DEFAULT 'normal',
    status          VARCHAR(20) DEFAULT 'pending',
    technician_id   BIGINT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_wo_item ON work_order_item(work_order_id);
```

#### `work_order_part` — 工单配件明细

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| work_order_id | BIGINT | |
| part_id | BIGINT | 配件 |
| name | VARCHAR(100) | 配件名称（冗余） |
| quantity | INT | 数量 |
| unit_price | DECIMAL(10,2) | 单价 |
| cost_price | DECIMAL(10,2) | 成本价（出库时快照） |
| amount | DECIMAL(10,2) | 小计 |
| status | VARCHAR(20) | pending/picked/returned |

```sql
CREATE TABLE work_order_part (
    id              BIGSERIAL PRIMARY KEY,
    work_order_id   BIGINT NOT NULL,
    part_id         BIGINT NOT NULL,
    name            VARCHAR(100) NOT NULL,
    quantity        INT NOT NULL DEFAULT 1,
    unit_price      DECIMAL(10,2) NOT NULL,
    cost_price      DECIMAL(10,2),
    amount          DECIMAL(10,2) NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_wo_part ON work_order_part(work_order_id);
```

#### `work_order_assignment` — 派工记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| work_order_id | BIGINT | |
| work_order_item_id | BIGINT | 具体项目 |
| technician_id | BIGINT | 技师 |
| work_bay_id | BIGINT | 工位 |
| status | VARCHAR(20) | assigned/started/paused/completed |
| started_at | TIMESTAMP | 开工 |
| finished_at | TIMESTAMP | 完工 |
| photos | JSONB | 施工照片 |

#### `work_order_log` — 工单状态日志

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| work_order_id | BIGINT | |
| from_status | VARCHAR(20) | 原状态 |
| to_status | VARCHAR(20) | 新状态 |
| operator_id | BIGINT | 操作人 |
| remark | VARCHAR(255) | 备注 |
| created_at | TIMESTAMP | |

```sql
CREATE TABLE work_order_log (
    id              BIGSERIAL PRIMARY KEY,
    work_order_id   BIGINT NOT NULL,
    from_status     VARCHAR(20),
    to_status       VARCHAR(20) NOT NULL,
    operator_id     BIGINT,
    remark          VARCHAR(255),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_wo_log ON work_order_log(work_order_id);
```

#### `work_order_attachment` — 工单附件

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| work_order_id | BIGINT | |
| type | VARCHAR(20) | photo/document |
| url | VARCHAR(500) | 文件 URL |
| description | VARCHAR(255) | 描述 |
| uploader_id | BIGINT | 上传人 |
| created_at | TIMESTAMP | |

---

### 3.6 收银结算

#### `payment` — 支付/结算

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | |
| work_order_id | BIGINT | 关联工单 |
| payment_no | VARCHAR(32) | 结算单号 |
| total_amount | DECIMAL(12,2) | 应收 |
| discount_amount | DECIMAL(12,2) | 折扣 |
| payable_amount | DECIMAL(12,2) | 应付 |
| paid_amount | DECIMAL(12,2) | 实付 |
| status | VARCHAR(20) | pending/paid/refunded/partial_refund |
| cashier_id | BIGINT | 收银员 |
| settled_at | TIMESTAMP | 结算时间 |

```sql
CREATE TABLE payment (
    id                  BIGSERIAL PRIMARY KEY,
    store_id            BIGINT NOT NULL,
    work_order_id       BIGINT NOT NULL,
    payment_no          VARCHAR(32) NOT NULL UNIQUE,
    total_amount        DECIMAL(12,2) NOT NULL,
    discount_amount     DECIMAL(12,2) DEFAULT 0,
    payable_amount      DECIMAL(12,2) NOT NULL,
    paid_amount         DECIMAL(12,2) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    cashier_id          BIGINT,
    settled_at          TIMESTAMP,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_payment_wo ON payment(work_order_id);
CREATE INDEX idx_payment_store ON payment(store_id, settled_at);
```

#### `payment_detail` — 支付明细

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| payment_id | BIGINT | |
| method | VARCHAR(20) | cash/wechat/alipay/bank/card |
| amount | DECIMAL(12,2) | 金额 |
| transaction_no | VARCHAR(64) | 第三方交易号 |
| status | VARCHAR(20) | success/failed/refunded |

```sql
CREATE TABLE payment_detail (
    id              BIGSERIAL PRIMARY KEY,
    payment_id      BIGINT NOT NULL,
    method          VARCHAR(20) NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    transaction_no  VARCHAR(64),
    status          VARCHAR(20) DEFAULT 'success',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_payment_detail ON payment_detail(payment_id);
```

---

### 3.7 会员与营销（二期）

#### `member_card` — 会员卡

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | |
| customer_id | BIGINT | |
| card_no | VARCHAR(32) | 卡号 |
| type | VARCHAR(20) | stored_value/count/package |
| balance | DECIMAL(12,2) | 余额（储值卡） |
| total_count | INT | 总次数（次卡） |
| used_count | INT | 已用次数 |
| status | VARCHAR(20) | active/expired/frozen |
| expired_at | TIMESTAMP | 过期时间 |

#### `member_card_log` — 会员卡流水

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| member_card_id | BIGINT | |
| type | VARCHAR(20) | recharge/consume/refund |
| amount | DECIMAL(12,2) | 变动金额 |
| balance_after | DECIMAL(12,2) | 变动后余额 |
| ref_type | VARCHAR(30) | 关联类型 |
| ref_id | BIGINT | 关联 ID |

#### `coupon` — 优惠券

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | |
| name | VARCHAR(100) | 券名称 |
| type | VARCHAR(20) | fixed/percent |
| value | DECIMAL(10,2) | 面值/折扣比 |
| min_amount | DECIMAL(10,2) | 最低消费 |
| total_count | INT | 发行总量 |
| used_count | INT | 已使用 |
| start_at | TIMESTAMP | 生效时间 |
| end_at | TIMESTAMP | 过期时间 |
| status | VARCHAR(20) | active/inactive |

#### `customer_coupon` — 客户优惠券

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| coupon_id | BIGINT | |
| customer_id | BIGINT | |
| status | VARCHAR(20) | unused/used/expired |
| used_at | TIMESTAMP | 使用时间 |
| payment_id | BIGINT | 使用于哪笔结算 |

---

### 3.8 员工业绩（二期）

#### `commission_rule` — 提成规则

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | |
| name | VARCHAR(50) | 规则名称 |
| target_type | VARCHAR(20) | service/part/labor |
| rate | DECIMAL(5,2) | 提成比例(%) |
| status | SMALLINT | |

#### `commission_record` — 提成记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | PK |
| store_id | BIGINT | |
| user_id | BIGINT | 员工 |
| work_order_id | BIGINT | |
| amount | DECIMAL(10,2) | 提成金额 |
| period | VARCHAR(7) | 月份 2026-09 |
| status | VARCHAR(20) | pending/confirmed/paid |

---

## 4. 索引策略

| 场景 | 索引 |
|------|------|
| 门店内查询 | 所有业务表 `(store_id, ...)` 复合索引 |
| 工单列表 | `(store_id, status, created_at DESC)` |
| 客户搜索 | `(store_id, phone)` + `(store_id, name)` |
| 车牌搜索 | `(store_id, plate_number)` |
| 库存查询 | `(store_id, part_id)` UNIQUE |
| 报表统计 | `(store_id, settled_at)` on payment |

---

## 5. 编号规则

| 类型 | 格式 | 示例 |
|------|------|------|
| 工单号 | WO + yyyyMMdd + 4位序号 | WO202609070001 |
| 结算单号 | PAY + yyyyMMdd + 4位序号 | PAY202609070001 |
| 入库单号 | IN + yyyyMMdd + 4位序号 | IN202609070001 |
| 会员卡号 | MC + 8位随机 | MC12345678 |

> 建议使用 Redis `INCR` 或数据库序列表生成当日序号，保证唯一。

---

## 6. 数据量预估（单店 3 年）

| 表 | 预估行数 | 说明 |
|----|----------|------|
| work_order | ~15,000 | 15台/天 × 365 × 3 |
| work_order_item | ~45,000 | 平均每单 3 个项目 |
| work_order_part | ~30,000 | 平均每单 2 个配件 |
| customer | ~5,000 | |
| vehicle | ~6,000 | |
| inventory_log | ~50,000 | |
| payment | ~15,000 | |

---

## 7. MVP 建表顺序

```
1. store, work_bay, user
2. customer, vehicle
3. service_category, service_item
4. part_category, part, supplier, inventory, inventory_log
5. work_order, work_order_inspection, work_order_item, work_order_part
6. work_order_assignment, work_order_log, work_order_attachment
7. payment, payment_detail
```

---

## 8. 迁移与种子数据

### 8.1 系统预设数据

- 服务分类：维修、保养、洗美、轮胎、其他
- 配件分类：油液、滤清、制动、点火、轮胎、其他
- 默认角色：老板、店长、前台、技师、仓管、财务

### 8.2 迁移工具

推荐使用 **Flyway** 或 **Alembic**（Python）/ **Prisma Migrate**（Node.js）管理数据库版本。
