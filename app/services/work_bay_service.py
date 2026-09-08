from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.dependencies import CurrentUser
from app.models.work_bay import WORK_BAY_BUSY, WORK_BAY_DISABLED, WORK_BAY_IDLE, WorkBay
from app.models.work_order import WO_CANCELLED, WO_COMPLETED, WorkOrder
from app.schemas.work_bay import WorkBayCreate, WorkBayResponse, WorkBayUpdate


class WorkBayService:
    @staticmethod
    def list_bays(db: Session, current_user: CurrentUser) -> list[WorkBayResponse]:
        bays = (
            db.query(WorkBay)
            .filter(WorkBay.store_id == current_user.store_id)
            .order_by(WorkBay.sort_order.asc(), WorkBay.id.asc())
            .all()
        )
        return [WorkBayResponse.model_validate(b) for b in bays]

    @staticmethod
    def create_bay(db: Session, current_user: CurrentUser, data: WorkBayCreate) -> WorkBayResponse:
        exists = (
            db.query(WorkBay)
            .filter(WorkBay.store_id == current_user.store_id, WorkBay.name == data.name)
            .first()
        )
        if exists:
            raise ConflictError("工位名称已存在")

        bay = WorkBay(store_id=current_user.store_id, **data.model_dump())
        db.add(bay)
        db.commit()
        db.refresh(bay)
        return WorkBayResponse.model_validate(bay)

    @staticmethod
    def update_bay(
        db: Session, current_user: CurrentUser, bay_id: int, data: WorkBayUpdate
    ) -> WorkBayResponse:
        bay = WorkBayService._get_bay_or_404(db, current_user, bay_id)

        if data.name is not None and data.name != bay.name:
            exists = (
                db.query(WorkBay)
                .filter(
                    WorkBay.store_id == current_user.store_id,
                    WorkBay.name == data.name,
                    WorkBay.id != bay_id,
                )
                .first()
            )
            if exists:
                raise ConflictError("工位名称已存在")

        for field in ("name", "type", "status", "sort_order"):
            value = getattr(data, field)
            if value is not None:
                setattr(bay, field, value)
        bay.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(bay)
        return WorkBayResponse.model_validate(bay)

    @staticmethod
    def delete_bay(db: Session, current_user: CurrentUser, bay_id: int) -> None:
        bay = WorkBayService._get_bay_or_404(db, current_user, bay_id)
        active = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.work_bay_id == bay_id,
                WorkOrder.store_id == current_user.store_id,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.status.notin_([WO_COMPLETED, WO_CANCELLED]),
            )
            .first()
        )
        if active:
            raise BadRequestError("工位上有进行中的工单，无法删除")
        db.delete(bay)
        db.commit()

    @staticmethod
    def assign_to_order(
        db: Session, current_user: CurrentUser, bay_id: int, work_order_id: int
    ) -> WorkBay:
        bay = WorkBayService._get_bay_or_404(db, current_user, bay_id)
        if bay.status == WORK_BAY_DISABLED:
            raise BadRequestError("工位已停用")

        other = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.work_bay_id == bay_id,
                WorkOrder.id != work_order_id,
                WorkOrder.store_id == current_user.store_id,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.status.notin_([WO_COMPLETED, WO_CANCELLED]),
            )
            .first()
        )
        if other:
            raise BadRequestError(f"工位「{bay.name}」已被工单 {other.order_no} 占用")

        bay.status = WORK_BAY_BUSY
        bay.updated_at = datetime.now(timezone.utc)
        return bay

    @staticmethod
    def release_from_order(db: Session, work_order: WorkOrder) -> None:
        if not work_order.work_bay_id:
            return
        bay = db.query(WorkBay).filter(WorkBay.id == work_order.work_bay_id).first()
        if not bay:
            return
        still_used = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.work_bay_id == bay.id,
                WorkOrder.id != work_order.id,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.status.notin_([WO_COMPLETED, WO_CANCELLED]),
            )
            .first()
        )
        if not still_used:
            bay.status = WORK_BAY_IDLE
            bay.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _get_bay_or_404(db: Session, current_user: CurrentUser, bay_id: int) -> WorkBay:
        bay = (
            db.query(WorkBay)
            .filter(WorkBay.id == bay_id, WorkBay.store_id == current_user.store_id)
            .first()
        )
        if bay is None:
            raise NotFoundError("工位不存在")
        return bay
