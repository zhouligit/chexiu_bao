from dataclasses import dataclass
from decimal import Decimal

TRIAL_DAYS = 14
GRACE_DAYS = 7

BILLING_CYCLES = {
    "monthly": {"label": "按月", "days": 30},
    "yearly": {"label": "按年", "days": 365},
    "lifetime": {"label": "终身买断", "days": None},
}


@dataclass(frozen=True)
class PlanPrice:
    monthly: Decimal | None
    yearly: Decimal | None
    lifetime: Decimal | None


@dataclass(frozen=True)
class SubscriptionPlanDef:
    code: str
    name: str
    description: str
    max_users: int
    features: tuple[str, ...]
    prices: PlanPrice


SUBSCRIPTION_PLANS: dict[str, SubscriptionPlanDef] = {
    "basic": SubscriptionPlanDef(
        code="basic",
        name="基础版",
        description="适合单店起步，覆盖接车开单、库存、报表核心流程",
        max_users=5,
        features=(
            "工单全流程",
            "客户/车辆管理",
            "库存管理",
            "经营报表",
            "最多 5 个员工账号",
        ),
        prices=PlanPrice(
            monthly=Decimal("9"),
            yearly=Decimal("99"),
            lifetime=Decimal("499"),
        ),
    ),
    "pro": SubscriptionPlanDef(
        code="pro",
        name="专业版",
        description="适合经营稳定的门店，解锁营销与高级能力",
        max_users=20,
        features=(
            "基础版全部功能",
            "会员储值/卡券（即将上线）",
            "员工业绩统计（即将上线）",
            "车主小程序（即将上线）",
            "最多 20 个员工账号",
            "优先客服支持",
        ),
        prices=PlanPrice(
            monthly=Decimal("19"),
            yearly=Decimal("199"),
            lifetime=Decimal("999"),
        ),
    ),
}

DEFAULT_PLAN_CODE = "basic"
