from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.dependencies import CurrentUser
from app.models.customer import Customer, Vehicle
from app.models.payment import Payment, PaymentDetail
from app.services.inventory_service import InventoryService
from app.services.work_bay_service import WorkBayService
from app.models.inventory import Part
from app.models.service_item import ServiceItem
from app.models.work_bay import WorkBay
from app.models.work_order import (
    WO_STATUS_LABELS,
    WO_TRANSITIONS,
    WorkOrder,
    WorkOrderItem,
    WorkOrderLog,
    WorkOrderPart,
)
from app.schemas.common import PageParams, PageResult
from app.schemas.work_order import (
    SettleRequest,
    WorkOrderCreate,
    WorkOrderDetail,
    WorkOrderItemCreate,
    WorkOrderListItem,
    WorkOrderPartCreate,
)
from app.utils.order_no import generate_serial_no


class WorkOrderService:
    @staticmethod
    def _calc_item_amount(quantity: Decimal, unit_price: Decimal, discount: Decimal) -> Decimal:
        return (quantity * unit_price * discount / Decimal("100")).quantize(Decimal("0.01"))

    @staticmethod
    def _recalc_amounts(work_order: WorkOrder) -> None:
        items_total = sum((item.amount for item in work_order.items), Decimal("0"))
        parts_total = sum((part.amount for part in work_order.parts), Decimal("0"))
        work_order.total_amount = items_total + parts_total
        work_order.payable_amount = work_order.total_amount - work_order.discount_amount

    @staticmethod
    def list_orders(db: Session, current_user: CurrentUser, params: PageParams) -> PageResult:
        query = db.query(WorkOrder).filter(
            WorkOrder.store_id == current_user.store_id,
            WorkOrder.deleted_at.is_(None),
        )
        if params.keyword:
            keyword = f"%{params.keyword}%"
            query = query.filter(WorkOrder.order_no.ilike(keyword))

        if params.status:
            query = query.filter(WorkOrder.status == params.status)

        total = query.count()
        orders = (
            query.order_by(WorkOrder.id.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
            .all()
        )

        customer_ids = {o.customer_id for o in orders}
        vehicle_ids = {o.vehicle_id for o in orders}
        customers = {
            c.id: c
            for c in db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
        } if customer_ids else {}
        vehicles = {
            v.id: v
            for v in db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()
        } if vehicle_ids else {}

        items = []
        for order in orders:
            customer = customers.get(order.customer_id)
            vehicle = vehicles.get(order.vehicle_id)
            items.append(
                WorkOrderListItem(
                    id=order.id,
                    order_no=order.order_no,
                    status=order.status,
                    status_label=WO_STATUS_LABELS.get(order.status, order.status),
                    customer_id=order.customer_id,
                    vehicle_id=order.vehicle_id,
                    customer_name=customer.name if customer else None,
                    plate_number=vehicle.plate_number if vehicle else None,
                    total_amount=float(order.total_amount),
                    payable_amount=float(order.payable_amount),
                    created_at=order.created_at,
                )
            )

        return PageResult(items=items, total=total, page=params.page, page_size=params.page_size)

    @staticmethod
    def create_order(db: Session, current_user: CurrentUser, data: WorkOrderCreate) -> WorkOrderDetail:
        customer = (
            db.query(Customer)
            .filter(
                Customer.id == data.customer_id,
                Customer.store_id == current_user.store_id,
                Customer.deleted_at.is_(None),
            )
            .first()
        )
        if not customer:
            raise NotFoundError("客户不存在")

        vehicle = (
            db.query(Vehicle)
            .filter(
                Vehicle.id == data.vehicle_id,
                Vehicle.customer_id == data.customer_id,
                Vehicle.store_id == current_user.store_id,
                Vehicle.deleted_at.is_(None),
            )
            .first()
        )
        if not vehicle:
            raise NotFoundError("车辆不存在")

        order_no = generate_serial_no(db, WorkOrder, "order_no", "WO")
        work_order = WorkOrder(
            store_id=current_user.store_id,
            order_no=order_no,
            customer_id=data.customer_id,
            vehicle_id=data.vehicle_id,
            receptionist_id=current_user.id,
            mileage_in=data.mileage_in,
            fuel_level=data.fuel_level,
            customer_request=data.customer_request,
            internal_note=data.internal_note,
        )
        db.add(work_order)
        db.flush()

        WorkOrderService._add_log(db, work_order.id, None, work_order.status, current_user.id, "接车开单")
        db.commit()
        return WorkOrderService.get_detail(db, current_user, work_order.id)

    @staticmethod
    def get_detail(db: Session, current_user: CurrentUser, order_id: int) -> WorkOrderDetail:
        work_order = WorkOrderService._get_order_or_404(db, current_user, order_id)
        customer = db.query(Customer).filter(Customer.id == work_order.customer_id).first()
        vehicle = db.query(Vehicle).filter(Vehicle.id == work_order.vehicle_id).first()

        detail = WorkOrderDetail.model_validate(work_order)
        detail.status_label = WO_STATUS_LABELS.get(work_order.status, work_order.status)
        if customer:
            detail.customer = {"id": customer.id, "name": customer.name, "phone": customer.phone}
        if vehicle:
            detail.vehicle = {
                "id": vehicle.id,
                "plate_number": vehicle.plate_number,
                "brand": vehicle.brand,
                "model": vehicle.model,
            }
        if work_order.work_bay_id:
            bay = (
                db.query(WorkBay)
                .filter(WorkBay.id == work_order.work_bay_id, WorkBay.store_id == current_user.store_id)
                .first()
            )
            if bay:
                detail.work_bay = {"id": bay.id, "name": bay.name}
        return detail

    @staticmethod
    def transition(db: Session, current_user: CurrentUser, order_id: int, to_status: str, remark: str | None):
        work_order = WorkOrderService._get_order_or_404(db, current_user, order_id)
        allowed = WO_TRANSITIONS.get(work_order.status, [])
        if to_status not in allowed:
            raise ConflictError(f"不能从「{WO_STATUS_LABELS.get(work_order.status)}」流转到「{WO_STATUS_LABELS.get(to_status, to_status)}」")

        if to_status == "pending_confirm" and not work_order.items:
            raise BadRequestError("请先添加服务项目再提交报价")

        if to_status == "pending_settle":
            work_order.finished_at = datetime.now(timezone.utc)

        if to_status == "in_progress":
            WorkOrderService._pick_pending_parts(db, current_user, work_order)

        if to_status == "cancelled":
            WorkOrderService._release_parts_on_cancel(db, current_user, work_order)
            WorkBayService.release_from_order(db, work_order)
            work_order.work_bay_id = None

        from_status = work_order.status
        work_order.status = to_status
        WorkOrderService._add_log(db, work_order.id, from_status, to_status, current_user.id, remark)
        db.commit()
        return WorkOrderService.get_detail(db, current_user, order_id)

    @staticmethod
    def add_item(db: Session, current_user: CurrentUser, order_id: int, data: WorkOrderItemCreate):
        work_order = WorkOrderService._get_order_or_404(db, current_user, order_id)

        if data.type == "addon":
            if work_order.status != "in_progress":
                raise BadRequestError("增项只能在施工中添加")
            item_status = "pending_confirm"
        elif work_order.status not in ("pending_quote", "pending_confirm", "in_progress"):
            raise BadRequestError("当前状态不可添加项目")
        else:
            item_status = "pending"

        amount = WorkOrderService._calc_item_amount(data.quantity, data.unit_price, data.discount)
        item = WorkOrderItem(
            work_order_id=work_order.id,
            service_item_id=data.service_item_id,
            name=data.name,
            quantity=data.quantity,
            unit_price=data.unit_price,
            discount=data.discount,
            amount=amount,
            labor_hours=data.labor_hours,
            type=data.type,
            status=item_status,
        )
        db.add(item)
        db.flush()
        db.refresh(work_order, ["items", "parts"])
        WorkOrderService._recalc_amounts(work_order)
        if data.type == "addon":
            WorkOrderService._add_log(
                db, work_order.id, work_order.status, work_order.status, current_user.id, f"新增增项：{data.name}"
            )
        db.commit()
        return WorkOrderService.get_detail(db, current_user, order_id)

    @staticmethod
    def confirm_addon_item(db: Session, current_user: CurrentUser, order_id: int, item_id: int):
        work_order = WorkOrderService._get_order_or_404(db, current_user, order_id)
        item = next((i for i in work_order.items if i.id == item_id), None)
        if item is None:
            raise NotFoundError("项目不存在")
        if item.type != "addon" or item.status != "pending_confirm":
            raise BadRequestError("该项目不是待确认的增项")

        item.status = "pending"
        WorkOrderService._add_log(
            db, work_order.id, work_order.status, work_order.status, current_user.id, f"客户确认增项：{item.name}"
        )
        db.commit()
        return WorkOrderService.get_detail(db, current_user, order_id)

    @staticmethod
    def update_item_status(
        db: Session, current_user: CurrentUser, order_id: int, item_id: int, status: str
    ):
        transitions = {
            "pending": {"in_progress"},
            "in_progress": {"paused", "completed"},
            "paused": {"in_progress"},
        }
        work_order = WorkOrderService._get_order_or_404(db, current_user, order_id)
        if work_order.status not in ("in_progress", "pending_qc"):
            raise BadRequestError("当前工单状态不可更新项目进度")

        item = next((i for i in work_order.items if i.id == item_id), None)
        if item is None:
            raise NotFoundError("项目不存在")
        if item.status == "pending_confirm":
            raise BadRequestError("增项需先经客户确认")
        allowed = transitions.get(item.status, set())
        if status not in allowed:
            raise BadRequestError(f"不能从「{item.status}」变更为「{status}」")

        item.status = status
        labels = {
            "in_progress": "开工",
            "paused": "暂停",
            "completed": "完工",
        }
        WorkOrderService._add_log(
            db,
            work_order.id,
            work_order.status,
            work_order.status,
            current_user.id,
            f"项目「{item.name}」{labels.get(status, status)}",
        )
        db.commit()
        return WorkOrderService.get_detail(db, current_user, order_id)

    @staticmethod
    def add_part(db: Session, current_user: CurrentUser, order_id: int, data: WorkOrderPartCreate):
        work_order = WorkOrderService._get_order_or_404(db, current_user, order_id)
        if work_order.status not in ("pending_quote", "pending_confirm", "in_progress"):
            raise BadRequestError("当前状态不可添加配件")

        cost_price = None
        part_name = data.name or ""
        unit_price = data.unit_price or Decimal("0")

        if data.part_id:
            part = (
                db.query(Part)
                .filter(
                    Part.id == data.part_id,
                    Part.store_id == current_user.store_id,
                    Part.deleted_at.is_(None),
                )
                .first()
            )
            if not part:
                raise NotFoundError("配件不存在")
            part_name = part.name
            if data.unit_price is None:
                unit_price = part.sell_price or Decimal("0")
            inv = InventoryService.lock(db, current_user, part.id, data.quantity, work_order.id)
            cost_price = inv.avg_cost
        elif data.unit_price is None or not part_name:
            raise BadRequestError("手动添加配件需填写名称和单价")

        amount = (Decimal(data.quantity) * unit_price).quantize(Decimal("0.01"))
        wo_part = WorkOrderPart(
            work_order_id=work_order.id,
            part_id=data.part_id,
            name=part_name,
            quantity=data.quantity,
            unit_price=unit_price,
            cost_price=cost_price,
            amount=amount,
            status="pending",
        )
        db.add(wo_part)
        db.flush()
        db.refresh(work_order, ["items", "parts"])
        WorkOrderService._recalc_amounts(work_order)
        db.commit()
        return WorkOrderService.get_detail(db, current_user, order_id)

    @staticmethod
    def settle(db: Session, current_user: CurrentUser, order_id: int, data: SettleRequest):
        work_order = WorkOrderService._get_order_or_404(db, current_user, order_id)
        if work_order.status != "pending_settle":
            raise BadRequestError("当前状态不可结算")

        WorkOrderService._pick_pending_parts(db, current_user, work_order)

        total_discount = data.discount_amount + data.round_down_amount
        if total_discount > work_order.total_amount:
            raise BadRequestError("折扣与抹零不能超过合计金额")

        work_order.discount_amount = total_discount
        WorkOrderService._recalc_amounts(work_order)

        paid_total = sum((p.amount for p in data.payments), Decimal("0"))
        if paid_total != work_order.payable_amount:
            raise BadRequestError(f"支付金额 ¥{paid_total} 与应付 ¥{work_order.payable_amount} 不一致")

        payment_no = generate_serial_no(db, Payment, "payment_no", "PAY")
        payment = Payment(
            store_id=current_user.store_id,
            work_order_id=work_order.id,
            payment_no=payment_no,
            total_amount=work_order.total_amount,
            discount_amount=work_order.discount_amount,
            payable_amount=work_order.payable_amount,
            paid_amount=paid_total,
            cashier_id=current_user.id,
            settled_at=datetime.now(timezone.utc),
        )
        db.add(payment)
        db.flush()

        for p in data.payments:
            db.add(
                PaymentDetail(
                    payment_id=payment.id,
                    method=p.method,
                    amount=p.amount,
                    created_at=datetime.now(timezone.utc),
                )
            )

        work_order.paid_amount = paid_total
        work_order.settled_at = datetime.now(timezone.utc)
        from_status = work_order.status
        work_order.status = "completed"
        WorkBayService.release_from_order(db, work_order)
        work_order.work_bay_id = None
        WorkOrderService._add_log(db, work_order.id, from_status, "completed", current_user.id, "结算完成")

        customer = db.query(Customer).filter(Customer.id == work_order.customer_id).first()
        if customer:
            customer.total_spent += work_order.paid_amount
            customer.visit_count += 1
            customer.last_visit_at = datetime.now(timezone.utc)

        db.commit()
        return WorkOrderService.get_detail(db, current_user, order_id)

    @staticmethod
    def assign_technician(db: Session, current_user: CurrentUser, order_id: int, data) -> object:
        from app.models.user import User

        work_order = WorkOrderService._get_order_or_404(db, current_user, order_id)
        technician = (
            db.query(User)
            .filter(
                User.id == data.technician_id,
                User.store_id == current_user.store_id,
                User.deleted_at.is_(None),
                User.status == 1,
            )
            .first()
        )
        if technician is None:
            raise NotFoundError("技师不存在")
        if technician.role not in ("technician", "manager", "owner"):
            raise BadRequestError("该员工不能作为施工技师")

        target_ids = set(data.item_ids) if data.item_ids else None
        updated = False
        for item in work_order.items:
            if target_ids is None or item.id in target_ids:
                item.technician_id = data.technician_id
                updated = True
        if not updated:
            raise BadRequestError("没有可派工的项目")

        if data.work_bay_id:
            if work_order.work_bay_id and work_order.work_bay_id != data.work_bay_id:
                WorkBayService.release_from_order(db, work_order)
            WorkBayService.assign_to_order(db, current_user, data.work_bay_id, work_order.id)
            work_order.work_bay_id = data.work_bay_id

        db.commit()
        return WorkOrderService.get_detail(db, current_user, order_id)

    @staticmethod
    def _get_order_or_404(db: Session, current_user: CurrentUser, order_id: int) -> WorkOrder:
        work_order = (
            db.query(WorkOrder)
            .options(
                joinedload(WorkOrder.items),
                joinedload(WorkOrder.parts),
                joinedload(WorkOrder.logs),
            )
            .filter(
                WorkOrder.id == order_id,
                WorkOrder.store_id == current_user.store_id,
                WorkOrder.deleted_at.is_(None),
            )
            .first()
        )
        if not work_order:
            raise NotFoundError("工单不存在")
        return work_order

    @staticmethod
    def _pick_pending_parts(db: Session, current_user: CurrentUser, work_order: WorkOrder) -> None:
        for wo_part in work_order.parts:
            if wo_part.part_id and wo_part.status == "pending":
                InventoryService.pick_out(
                    db, current_user, wo_part.part_id, wo_part.quantity, work_order.id
                )
                wo_part.status = "picked"

    @staticmethod
    def _release_parts_on_cancel(db: Session, current_user: CurrentUser, work_order: WorkOrder) -> None:
        for wo_part in work_order.parts:
            if not wo_part.part_id:
                continue
            if wo_part.status == "pending":
                InventoryService.unlock(
                    db, current_user, wo_part.part_id, wo_part.quantity, work_order.id
                )
                wo_part.status = "returned"
            elif wo_part.status == "picked":
                InventoryService.return_stock(
                    db, current_user, wo_part.part_id, wo_part.quantity, work_order.id
                )
                wo_part.status = "returned"

    @staticmethod
    def _add_log(
        db: Session,
        work_order_id: int,
        from_status: str | None,
        to_status: str,
        operator_id: int,
        remark: str | None,
    ) -> None:
        db.add(
            WorkOrderLog(
                work_order_id=work_order_id,
                from_status=from_status,
                to_status=to_status,
                operator_id=operator_id,
                remark=remark,
                created_at=datetime.now(timezone.utc),
            )
        )


class ServiceItemService:
    @staticmethod
    def list_items(db: Session, current_user: CurrentUser, include_disabled: bool = False) -> list:
        query = db.query(ServiceItem).filter(
            ServiceItem.store_id == current_user.store_id,
            ServiceItem.deleted_at.is_(None),
        )
        if not include_disabled:
            query = query.filter(ServiceItem.status == 1)
        items = query.order_by(ServiceItem.id).all()
        from app.schemas.service_item import ServiceItemResponse

        return [ServiceItemResponse.model_validate(i) for i in items]

    @staticmethod
    def create_item(db: Session, current_user: CurrentUser, data):
        from app.schemas.service_item import ServiceItemResponse

        item = ServiceItem(store_id=current_user.store_id, **data.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return ServiceItemResponse.model_validate(item)

    @staticmethod
    def update_item(db: Session, current_user: CurrentUser, item_id: int, data):
        from app.schemas.service_item import ServiceItemResponse

        item = ServiceItemService._get_item_or_404(db, current_user, item_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return ServiceItemResponse.model_validate(item)

    @staticmethod
    def delete_item(db: Session, current_user: CurrentUser, item_id: int) -> None:
        item = ServiceItemService._get_item_or_404(db, current_user, item_id)
        item.deleted_at = datetime.now(timezone.utc)
        item.status = 0
        db.commit()

    @staticmethod
    def _get_item_or_404(db: Session, current_user: CurrentUser, item_id: int) -> ServiceItem:
        item = (
            db.query(ServiceItem)
            .filter(
                ServiceItem.id == item_id,
                ServiceItem.store_id == current_user.store_id,
                ServiceItem.deleted_at.is_(None),
            )
            .first()
        )
        if item is None:
            raise NotFoundError("服务项目不存在")
        return item
