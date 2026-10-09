from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.current_user import CurrentUser
from app.models.appointment import (
    APPT_ARRIVED,
    APPT_CANCELLED,
    APPT_CONFIRMED,
    APPT_CONVERTED,
    APPT_PENDING,
    APPT_STATUS_LABELS,
    APPT_TRANSITIONS,
    Appointment,
)
from app.models.customer import Customer, Vehicle
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentConvertRequest,
    AppointmentCreate,
    AppointmentItem,
    AppointmentUpdate,
)
from app.schemas.common import PageParams, PageResult
from app.schemas.work_order import WorkOrderCreate
from app.services.work_order_service import WorkOrderService

SOURCE_LABELS = {
    "mp_owner": "车主小程序",
    "mp_store": "门店登记",
    "phone": "电话预约",
}


class AppointmentService:
    @staticmethod
    def _ids_to_str(ids: list[int] | None) -> str | None:
        if not ids:
            return None
        return ",".join(str(i) for i in ids)

    @staticmethod
    def _to_item(row: Appointment) -> AppointmentItem:
        return AppointmentItem(
            id=row.id,
            status=row.status,
            status_label=APPT_STATUS_LABELS.get(row.status, row.status),
            contact_name=row.contact_name,
            contact_phone=row.contact_phone,
            plate_number=row.plate_number,
            scheduled_start=row.scheduled_start,
            scheduled_end=row.scheduled_end,
            source=row.source,
            source_label=SOURCE_LABELS.get(row.source, row.source),
            customer_id=row.customer_id,
            vehicle_id=row.vehicle_id,
            work_order_id=row.work_order_id,
            deposit_amount=float(row.deposit_amount or 0),
            pay_status=row.pay_status,
            service_item_ids=row.service_item_ids,
            remark=row.remark,
            created_at=row.created_at,
        )

    @staticmethod
    def _get_or_404(db: Session, current_user: CurrentUser, appt_id: int) -> Appointment:
        row = (
            db.query(Appointment)
            .filter(
                Appointment.id == appt_id,
                Appointment.store_id == current_user.store_id,
                Appointment.deleted_at.is_(None),
            )
            .first()
        )
        if row is None:
            raise NotFoundError("预约不存在")
        return row

    @staticmethod
    def _assert_transition(row: Appointment, to_status: str) -> None:
        allowed = APPT_TRANSITIONS.get(row.status, [])
        if to_status not in allowed:
            raise ConflictError(
                f"不能从「{APPT_STATUS_LABELS.get(row.status)}」变更为「{APPT_STATUS_LABELS.get(to_status, to_status)}」"
            )

    @staticmethod
    def list_appointments(
        db: Session,
        current_user: CurrentUser,
        params: PageParams,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> PageResult:
        query = db.query(Appointment).filter(
            Appointment.store_id == current_user.store_id,
            Appointment.deleted_at.is_(None),
        )
        if params.status:
            query = query.filter(Appointment.status == params.status)
        if params.keyword:
            kw = f"%{params.keyword.strip()}%"
            query = query.filter(
                or_(
                    Appointment.contact_name.ilike(kw),
                    Appointment.contact_phone.ilike(kw),
                    Appointment.plate_number.ilike(kw),
                )
            )
        if date_from:
            query = query.filter(Appointment.scheduled_start >= date_from)
        if date_to:
            query = query.filter(Appointment.scheduled_start < date_to)

        total = query.count()
        rows = (
            query.order_by(Appointment.scheduled_start.asc(), Appointment.id.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
            .all()
        )
        return PageResult(
            items=[AppointmentService._to_item(r) for r in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    @staticmethod
    def get_detail(db: Session, current_user: CurrentUser, appt_id: int) -> AppointmentItem:
        return AppointmentService._to_item(AppointmentService._get_or_404(db, current_user, appt_id))

    @staticmethod
    def create(db: Session, current_user: CurrentUser, data: AppointmentCreate) -> AppointmentItem:
        if data.scheduled_end and data.scheduled_end <= data.scheduled_start:
            raise BadRequestError("结束时间必须晚于开始时间")

        row = Appointment(
            store_id=current_user.store_id,
            customer_id=data.customer_id,
            vehicle_id=data.vehicle_id,
            contact_name=data.contact_name.strip(),
            contact_phone=data.contact_phone.strip(),
            plate_number=(data.plate_number or "").strip().upper() or None,
            scheduled_start=data.scheduled_start,
            scheduled_end=data.scheduled_end,
            status=APPT_PENDING,
            source=data.source,
            deposit_amount=data.deposit_amount or Decimal("0"),
            pay_status="unpaid",
            service_item_ids=AppointmentService._ids_to_str(data.service_item_ids),
            remark=data.remark,
            created_by=current_user.id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return AppointmentService._to_item(row)

    @staticmethod
    def update(db: Session, current_user: CurrentUser, appt_id: int, data: AppointmentUpdate) -> AppointmentItem:
        row = AppointmentService._get_or_404(db, current_user, appt_id)
        if row.status in (APPT_CANCELLED, APPT_CONVERTED, "expired"):
            raise ConflictError("该预约已结束，无法修改")

        payload = data.model_dump(exclude_unset=True)
        if "service_item_ids" in payload:
            row.service_item_ids = AppointmentService._ids_to_str(payload.pop("service_item_ids"))
        if "plate_number" in payload and payload["plate_number"]:
            payload["plate_number"] = payload["plate_number"].strip().upper()
        if "contact_name" in payload and payload["contact_name"]:
            payload["contact_name"] = payload["contact_name"].strip()
        if "contact_phone" in payload and payload["contact_phone"]:
            payload["contact_phone"] = payload["contact_phone"].strip()

        start = payload.get("scheduled_start", row.scheduled_start)
        end = payload.get("scheduled_end", row.scheduled_end)
        if end and start and end <= start:
            raise BadRequestError("结束时间必须晚于开始时间")

        for key, value in payload.items():
            setattr(row, key, value)

        db.commit()
        db.refresh(row)
        return AppointmentService._to_item(row)

    @staticmethod
    def confirm(db: Session, current_user: CurrentUser, appt_id: int) -> AppointmentItem:
        row = AppointmentService._get_or_404(db, current_user, appt_id)
        AppointmentService._assert_transition(row, APPT_CONFIRMED)
        row.status = APPT_CONFIRMED
        db.commit()
        db.refresh(row)
        return AppointmentService._to_item(row)

    @staticmethod
    def arrive(db: Session, current_user: CurrentUser, appt_id: int) -> AppointmentItem:
        row = AppointmentService._get_or_404(db, current_user, appt_id)
        AppointmentService._assert_transition(row, APPT_ARRIVED)
        row.status = APPT_ARRIVED
        db.commit()
        db.refresh(row)
        return AppointmentService._to_item(row)

    @staticmethod
    def cancel(
        db: Session,
        current_user: CurrentUser,
        appt_id: int,
        data: AppointmentCancelRequest | None = None,
    ) -> AppointmentItem:
        row = AppointmentService._get_or_404(db, current_user, appt_id)
        AppointmentService._assert_transition(row, APPT_CANCELLED)
        row.status = APPT_CANCELLED
        if data and data.remark:
            note = data.remark.strip()
            row.remark = f"{row.remark}\n[取消] {note}".strip() if row.remark else f"[取消] {note}"
        db.commit()
        db.refresh(row)
        return AppointmentService._to_item(row)

    @staticmethod
    def _ensure_customer_vehicle(
        db: Session,
        current_user: CurrentUser,
        row: Appointment,
    ) -> tuple[int, int]:
        customer_id = row.customer_id
        vehicle_id = row.vehicle_id

        if customer_id:
            customer = (
                db.query(Customer)
                .filter(
                    Customer.id == customer_id,
                    Customer.store_id == current_user.store_id,
                    Customer.deleted_at.is_(None),
                )
                .first()
            )
            if not customer:
                raise NotFoundError("关联客户不存在")
        else:
            # 按手机号复用或新建
            customer = (
                db.query(Customer)
                .filter(
                    Customer.store_id == current_user.store_id,
                    Customer.phone == row.contact_phone,
                    Customer.deleted_at.is_(None),
                )
                .first()
            )
            if customer is None:
                customer = Customer(
                    store_id=current_user.store_id,
                    name=row.contact_name,
                    phone=row.contact_phone,
                    source=row.source,
                    remark="由预约自动建档",
                )
                db.add(customer)
                db.flush()
            customer_id = customer.id
            row.customer_id = customer_id

        plate = (row.plate_number or "").strip().upper()
        if not plate:
            raise BadRequestError("转工单需要车牌号，请先补充")

        if vehicle_id:
            vehicle = (
                db.query(Vehicle)
                .filter(
                    Vehicle.id == vehicle_id,
                    Vehicle.store_id == current_user.store_id,
                    Vehicle.deleted_at.is_(None),
                )
                .first()
            )
            if not vehicle:
                raise NotFoundError("关联车辆不存在")
            if vehicle.customer_id != customer_id:
                raise BadRequestError("车辆与客户不匹配")
        else:
            vehicle = (
                db.query(Vehicle)
                .filter(
                    Vehicle.store_id == current_user.store_id,
                    Vehicle.plate_number == plate,
                    Vehicle.deleted_at.is_(None),
                )
                .first()
            )
            if vehicle is None:
                vehicle = Vehicle(
                    store_id=current_user.store_id,
                    customer_id=customer_id,
                    plate_number=plate,
                )
                db.add(vehicle)
                db.flush()
            elif vehicle.customer_id != customer_id:
                raise ConflictError("该车牌已绑定其他客户")
            vehicle_id = vehicle.id
            row.vehicle_id = vehicle_id
            row.plate_number = plate

        return customer_id, vehicle_id

    @staticmethod
    def convert(
        db: Session,
        current_user: CurrentUser,
        appt_id: int,
        data: AppointmentConvertRequest | None = None,
    ) -> AppointmentItem:
        row = AppointmentService._get_or_404(db, current_user, appt_id)
        AppointmentService._assert_transition(row, APPT_CONVERTED)

        customer_id, vehicle_id = AppointmentService._ensure_customer_vehicle(db, current_user, row)
        data = data or AppointmentConvertRequest()
        request_text = data.customer_request or row.remark

        # create_order 内部会 commit；先 flush 预约关联字段
        db.flush()
        detail = WorkOrderService.create_order(
            db,
            current_user,
            WorkOrderCreate(
                customer_id=customer_id,
                vehicle_id=vehicle_id,
                mileage_in=data.mileage_in,
                fuel_level=data.fuel_level,
                customer_request=request_text,
                internal_note=f"来自预约#{row.id}",
            ),
        )

        # create_order 已 commit，重新加载预约
        row = AppointmentService._get_or_404(db, current_user, appt_id)
        row.status = APPT_CONVERTED
        row.work_order_id = detail.id
        row.customer_id = customer_id
        row.vehicle_id = vehicle_id
        db.commit()
        db.refresh(row)
        return AppointmentService._to_item(row)
