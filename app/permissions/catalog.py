"""Global permission catalog and default role → permission mapping."""

from __future__ import annotations

from typing import TypedDict

# (code, module, name, sort)
PERMISSIONS: tuple[tuple[str, str, str, int], ...] = (
    ("menu:dashboard", "menu", "首页看板", 10),
    ("menu:work_orders", "menu", "工单管理", 20),
    ("menu:customers", "menu", "客户管理", 30),
    ("menu:services", "menu", "服务项目", 40),
    ("menu:inventory", "menu", "库存管理", 50),
    ("menu:suppliers", "menu", "供应商", 60),
    ("menu:payments", "menu", "收退款", 70),
    ("menu:reports", "menu", "经营报表", 80),
    ("menu:settings", "menu", "系统设置", 90),
    ("work_order:read", "work_order", "查看工单", 100),
    ("work_order:create", "work_order", "创建工单", 110),
    ("work_order:update", "work_order", "更新工单/项目", 120),
    ("work_order:assign", "work_order", "派工", 130),
    ("work_order:settle", "work_order", "结算工单", 140),
    ("work_order:inspection", "work_order", "预检/检测", 150),
    ("work_order:print", "work_order", "打印工单", 160),
    ("customer:read", "customer", "查看客户", 200),
    ("customer:write", "customer", "编辑客户", 210),
    ("customer:delete", "customer", "删除客户", 220),
    ("customer:vehicle_manage", "customer", "车辆档案管理", 230),
    ("appointment:read", "appointment", "查看预约", 300),
    ("appointment:write", "appointment", "创建/编辑预约", 310),
    ("appointment:confirm", "appointment", "确认预约", 320),
    ("appointment:arrive", "appointment", "到店登记", 330),
    ("appointment:cancel", "appointment", "取消预约", 340),
    ("appointment:convert", "appointment", "预约转工单", 350),
    ("service_item:read", "service", "查看服务项目", 400),
    ("service_item:manage", "service", "管理服务项目", 410),
    ("inventory:read", "inventory", "查看库存", 500),
    ("inventory:part_manage", "inventory", "配件资料维护", 510),
    ("inventory:stock_in", "inventory", "入库", 520),
    ("inventory:stock_out", "inventory", "出库", 530),
    ("supplier:read", "supplier", "查看供应商", 600),
    ("supplier:manage", "supplier", "管理供应商", 610),
    ("payment:read", "payment", "查看收退款", 700),
    ("payment:refund", "payment", "退款", 710),
    ("report:overview", "report", "经营概览", 800),
    ("report:operations", "report", "运营日报", 810),
    ("report:finance", "report", "财务报表", 820),
    ("settings:store", "settings", "门店信息", 900),
    ("settings:users", "settings", "员工管理", 910),
    ("settings:work_bay", "settings", "工位管理", 920),
    ("settings:subscription", "settings", "订阅套餐", 930),
    ("subscription:manage", "subscription", "订阅下单/取消", 940),
    ("subscription:activate", "subscription", "激活订阅", 950),
    ("user:read", "user", "查看员工", 1000),
    ("user:create", "user", "新增员工", 1010),
    ("user:update", "user", "编辑员工", 1020),
    ("user:delete", "user", "删除员工", 1030),
    ("role:read", "role", "查看角色权限", 1100),
    ("role:manage", "role", "管理角色权限", 1110),
    ("upload:use", "common", "上传文件/OCR", 1200),
)

ALL_PERMISSION_CODES: frozenset[str] = frozenset(p[0] for p in PERMISSIONS)

SYSTEM_ROLE_SLUGS = ("owner", "manager", "receptionist", "technician", "warehouse", "finance")

ROLE_LABELS: dict[str, str] = {
    "owner": "老板",
    "manager": "店长",
    "receptionist": "前台",
    "technician": "技师",
    "warehouse": "仓管",
    "finance": "财务",
}


class DataPolicy(TypedDict, total=False):
    work_order: dict[str, str]
    appointment: dict[str, str]


def default_data_policy_for_slug(slug: str) -> dict:
    if slug == "technician":
        return {
            "work_order": {"visibility": "assigned_only"},
            "appointment": {"visibility": "store"},
        }
    return {
        "work_order": {"visibility": "store"},
        "appointment": {"visibility": "store"},
    }


def _all_except(*codes: str) -> frozenset[str]:
    return ALL_PERMISSION_CODES - frozenset(codes)


def permissions_for_role_slug(slug: str) -> frozenset[str]:
    if slug == "owner":
        return ALL_PERMISSION_CODES
    if slug == "manager":
        return _all_except("user:delete", "subscription:activate")
    if slug == "receptionist":
        return frozenset(
            {
                "menu:dashboard",
                "menu:work_orders",
                "menu:customers",
                "menu:services",
                "menu:reports",
                "menu:settings",
                "work_order:read",
                "work_order:create",
                "work_order:update",
                "work_order:assign",
                "work_order:settle",
                "work_order:inspection",
                "work_order:print",
                "customer:read",
                "customer:write",
                "customer:vehicle_manage",
                "appointment:read",
                "appointment:write",
                "appointment:confirm",
                "appointment:arrive",
                "appointment:cancel",
                "appointment:convert",
                "service_item:read",
                "inventory:read",
                "report:overview",
                "report:operations",
                "settings:store",
                "user:read",
                "upload:use",
            }
        )
    if slug == "technician":
        return frozenset(
            {
                "menu:dashboard",
                "menu:work_orders",
                "work_order:read",
                "work_order:update",
                "work_order:print",
                "appointment:read",
                "appointment:arrive",
                "upload:use",
            }
        )
    if slug == "warehouse":
        return frozenset(
            {
                "menu:inventory",
                "menu:suppliers",
                "menu:settings",
                "inventory:read",
                "inventory:part_manage",
                "inventory:stock_in",
                "inventory:stock_out",
                "supplier:read",
                "supplier:manage",
                "settings:store",
                "upload:use",
            }
        )
    if slug == "finance":
        return frozenset(
            {
                "menu:dashboard",
                "menu:work_orders",
                "menu:payments",
                "menu:reports",
                "work_order:read",
                "work_order:settle",
                "work_order:print",
                "payment:read",
                "payment:refund",
                "report:overview",
                "report:finance",
            }
        )
    return frozenset({"menu:dashboard", "work_order:read", "customer:read"})
