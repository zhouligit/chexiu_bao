from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.dependencies import CurrentUser
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate


class SupplierService:
    @staticmethod
    def list_suppliers(db: Session, current_user: CurrentUser) -> list[SupplierResponse]:
        items = (
            db.query(Supplier)
            .filter(Supplier.store_id == current_user.store_id, Supplier.deleted_at.is_(None))
            .order_by(Supplier.id.desc())
            .all()
        )
        return [SupplierResponse.model_validate(i) for i in items]

    @staticmethod
    def create_supplier(db: Session, current_user: CurrentUser, data: SupplierCreate) -> SupplierResponse:
        supplier = Supplier(store_id=current_user.store_id, **data.model_dump())
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
        return SupplierResponse.model_validate(supplier)

    @staticmethod
    def update_supplier(
        db: Session, current_user: CurrentUser, supplier_id: int, data: SupplierUpdate
    ) -> SupplierResponse:
        supplier = SupplierService._get_or_404(db, current_user, supplier_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(supplier, key, value)
        db.commit()
        db.refresh(supplier)
        return SupplierResponse.model_validate(supplier)

    @staticmethod
    def delete_supplier(db: Session, current_user: CurrentUser, supplier_id: int) -> None:
        supplier = SupplierService._get_or_404(db, current_user, supplier_id)
        supplier.deleted_at = datetime.now(timezone.utc)
        db.commit()

    @staticmethod
    def _get_or_404(db: Session, current_user: CurrentUser, supplier_id: int) -> Supplier:
        supplier = (
            db.query(Supplier)
            .filter(
                Supplier.id == supplier_id,
                Supplier.store_id == current_user.store_id,
                Supplier.deleted_at.is_(None),
            )
            .first()
        )
        if supplier is None:
            raise NotFoundError("供应商不存在")
        return supplier
