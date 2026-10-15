from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.dependencies import CurrentUser
from app.models.user import User
from app.models.work_order import WorkOrder, WorkOrderItem
from app.services.permission_service import PermissionService


class DataScope:
    @staticmethod
    def apply_work_order_query(db: Session, query: Query, current_user: CurrentUser) -> Query:
        user = db.query(User).filter(User.id == current_user.id).first()
        if user is None:
            return query.filter(False)
        visibility = PermissionService.work_order_visibility(db, user)
        if visibility != "assigned_only":
            return query
        assigned_order_ids = (
            db.query(WorkOrderItem.work_order_id)
            .join(WorkOrder, WorkOrder.id == WorkOrderItem.work_order_id)
            .filter(
                WorkOrder.store_id == current_user.store_id,
                WorkOrder.deleted_at.is_(None),
                or_(
                    WorkOrderItem.technician_id == current_user.id,
                    WorkOrder.receptionist_id == current_user.id,
                ),
            )
            .distinct()
        )
        return query.filter(
            or_(
                WorkOrder.id.in_(assigned_order_ids),
                WorkOrder.receptionist_id == current_user.id,
            )
        )

    @staticmethod
    def can_access_work_order(db: Session, current_user: CurrentUser, work_order: WorkOrder) -> bool:
        user = db.query(User).filter(User.id == current_user.id).first()
        if user is None:
            return False
        visibility = PermissionService.work_order_visibility(db, user)
        if visibility != "assigned_only":
            return True
        if work_order.receptionist_id == current_user.id:
            return True
        has_item = (
            db.query(WorkOrderItem.id)
            .filter(
                WorkOrderItem.work_order_id == work_order.id,
                WorkOrderItem.technician_id == current_user.id,
            )
            .first()
        )
        return has_item is not None
