from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.dependencies import CurrentUser
from app.models.supplier import WorkOrderInspection
from app.models.work_order import WO_PENDING_INSPECTION, WO_PENDING_QUOTE, WorkOrder
from app.schemas.inspection import (
    DEFAULT_PRE_CHECK_ITEMS,
    InspectionResponse,
    InspectionSubmit,
)


class InspectionService:
    @staticmethod
    def get_default_items() -> list[dict]:
        return DEFAULT_PRE_CHECK_ITEMS.copy()

    @staticmethod
    def get_inspection(db: Session, current_user: CurrentUser, order_id: int) -> InspectionResponse | None:
        InspectionService._get_order_or_404(db, current_user, order_id)
        record = (
            db.query(WorkOrderInspection)
            .filter(WorkOrderInspection.work_order_id == order_id, WorkOrderInspection.type == "pre_check")
            .order_by(WorkOrderInspection.id.desc())
            .first()
        )
        if record is None:
            return None
        return InspectionResponse.model_validate(record)

    @staticmethod
    def submit_inspection(
        db: Session, current_user: CurrentUser, order_id: int, data: InspectionSubmit
    ) -> InspectionResponse:
        work_order = InspectionService._get_order_or_404(db, current_user, order_id)
        if work_order.status not in (WO_PENDING_INSPECTION, WO_PENDING_QUOTE):
            raise BadRequestError("当前状态不可提交预检")

        items_data = [item.model_dump() for item in data.items]
        existing = (
            db.query(WorkOrderInspection)
            .filter(
                WorkOrderInspection.work_order_id == order_id,
                WorkOrderInspection.type == data.type,
            )
            .first()
        )
        if existing:
            existing.items = items_data
            existing.photos = data.photos
            existing.valuables = data.valuables
            existing.inspector_id = current_user.id
            record = existing
        else:
            record = WorkOrderInspection(
                work_order_id=order_id,
                type=data.type,
                items=items_data,
                photos=data.photos,
                valuables=data.valuables,
                inspector_id=current_user.id,
            )
            db.add(record)

        if data.finish and work_order.status == WO_PENDING_INSPECTION:
            from app.services.work_order_service import WorkOrderService

            WorkOrderService._add_log(
                db, work_order.id, work_order.status, WO_PENDING_QUOTE, current_user.id, "预检完成"
            )
            work_order.status = WO_PENDING_QUOTE

        db.commit()
        db.refresh(record)
        return InspectionResponse.model_validate(record)

    @staticmethod
    def _get_order_or_404(db: Session, current_user: CurrentUser, order_id: int) -> WorkOrder:
        work_order = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.id == order_id,
                WorkOrder.store_id == current_user.store_id,
                WorkOrder.deleted_at.is_(None),
            )
            .first()
        )
        if work_order is None:
            raise NotFoundError("工单不存在")
        return work_order
