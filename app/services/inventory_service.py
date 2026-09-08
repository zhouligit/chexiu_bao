from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.dependencies import CurrentUser
from app.models.inventory import Inventory, InventoryLog, Part
from app.schemas.inventory import InventoryLogResponse, PartCreate, PartUpdate, PartWithStock, StockInRequest, StockOutRequest


class InventoryService:
    @staticmethod
    def available_quantity(inventory: Inventory) -> int:
        return inventory.quantity - inventory.locked_quantity

    @staticmethod
    def get_inventory(db: Session, store_id: int, part_id: int) -> Inventory:
        inv = (
            db.query(Inventory)
            .filter(Inventory.store_id == store_id, Inventory.part_id == part_id)
            .first()
        )
        if not inv:
            inv = Inventory(store_id=store_id, part_id=part_id, quantity=0, locked_quantity=0, updated_at=datetime.now(timezone.utc))
            db.add(inv)
            db.flush()
        return inv

    @staticmethod
    def _log(
        db: Session,
        store_id: int,
        part_id: int,
        log_type: str,
        quantity: int,
        before_qty: int,
        after_qty: int,
        operator_id: int | None,
        ref_type: str | None = None,
        ref_id: int | None = None,
        remark: str | None = None,
    ) -> None:
        db.add(
            InventoryLog(
                store_id=store_id,
                part_id=part_id,
                type=log_type,
                quantity=quantity,
                before_qty=before_qty,
                after_qty=after_qty,
                ref_type=ref_type,
                ref_id=ref_id,
                remark=remark,
                operator_id=operator_id,
                created_at=datetime.now(timezone.utc),
            )
        )

    @staticmethod
    def list_parts(db: Session, current_user: CurrentUser, keyword: str | None = None) -> list[PartWithStock]:
        query = db.query(Part).filter(
            Part.store_id == current_user.store_id,
            Part.deleted_at.is_(None),
            Part.status == 1,
        )
        if keyword:
            kw = f"%{keyword}%"
            query = query.filter(Part.name.ilike(kw) | Part.code.ilike(kw))

        parts = query.order_by(Part.id.desc()).all()
        part_ids = [p.id for p in parts]
        inventories = {
            i.part_id: i
            for i in db.query(Inventory).filter(
                Inventory.store_id == current_user.store_id,
                Inventory.part_id.in_(part_ids),
            ).all()
        } if part_ids else {}

        result = []
        for part in parts:
            inv = inventories.get(part.id)
            qty = inv.quantity if inv else 0
            locked = inv.locked_quantity if inv else 0
            available = qty - locked
            result.append(
                PartWithStock(
                    id=part.id,
                    store_id=part.store_id,
                    name=part.name,
                    code=part.code,
                    brand=part.brand,
                    spec=part.spec,
                    unit=part.unit,
                    purchase_price=float(part.purchase_price) if part.purchase_price else None,
                    sell_price=float(part.sell_price) if part.sell_price else None,
                    safe_stock=part.safe_stock,
                    status=part.status,
                    quantity=qty,
                    locked_quantity=locked,
                    available_quantity=available,
                    avg_cost=float(inv.avg_cost) if inv and inv.avg_cost else None,
                    is_low_stock=available <= part.safe_stock,
                )
            )
        return result

    @staticmethod
    def create_part(db: Session, current_user: CurrentUser, data: PartCreate) -> PartWithStock:
        if data.code:
            exists = (
                db.query(Part)
                .filter(
                    Part.store_id == current_user.store_id,
                    Part.code == data.code,
                    Part.deleted_at.is_(None),
                )
                .first()
            )
            if exists:
                raise ConflictError("配件编码已存在")

        part = Part(
            store_id=current_user.store_id,
            name=data.name,
            code=data.code,
            brand=data.brand,
            spec=data.spec,
            unit=data.unit,
            purchase_price=data.purchase_price,
            sell_price=data.sell_price,
            safe_stock=data.safe_stock,
        )
        db.add(part)
        db.flush()

        if data.initial_stock > 0:
            InventoryService.stock_in(
                db,
                current_user,
                StockInRequest(
                    part_id=part.id,
                    quantity=data.initial_stock,
                    unit_cost=data.purchase_price,
                    remark="初始入库",
                ),
            )
        else:
            InventoryService.get_inventory(db, current_user.store_id, part.id)

        db.commit()
        items = InventoryService.list_parts(db, current_user)
        return next(i for i in items if i.id == part.id)

    @staticmethod
    def update_part(db: Session, current_user: CurrentUser, part_id: int, data: PartUpdate) -> PartWithStock:
        part = InventoryService._get_part_or_404(db, current_user, part_id)

        if data.code is not None and data.code != part.code:
            exists = (
                db.query(Part)
                .filter(
                    Part.store_id == current_user.store_id,
                    Part.code == data.code,
                    Part.deleted_at.is_(None),
                    Part.id != part_id,
                )
                .first()
            )
            if exists:
                raise ConflictError("配件编码已存在")

        for field in ("name", "code", "brand", "spec", "unit", "purchase_price", "sell_price", "safe_stock"):
            value = getattr(data, field)
            if value is not None:
                setattr(part, field, value)

        db.commit()
        items = InventoryService.list_parts(db, current_user)
        return next(i for i in items if i.id == part.id)

    @staticmethod
    def stock_out(db: Session, current_user: CurrentUser, data: StockOutRequest) -> PartWithStock:
        part = InventoryService._get_part_or_404(db, current_user, data.part_id)
        inv = InventoryService.get_inventory(db, current_user.store_id, part.id)
        available = InventoryService.available_quantity(inv)
        if data.quantity > available:
            raise BadRequestError(f"「{part.name}」可用库存不足，当前可用 {available}")

        before = inv.quantity
        inv.quantity -= data.quantity
        inv.updated_at = datetime.now(timezone.utc)

        InventoryService._log(
            db,
            current_user.store_id,
            part.id,
            "out",
            -data.quantity,
            before,
            inv.quantity,
            current_user.id,
            remark=data.remark or "手动出库",
        )
        db.commit()
        items = InventoryService.list_parts(db, current_user)
        return next(i for i in items if i.id == part.id)

    @staticmethod
    def list_logs(
        db: Session,
        current_user: CurrentUser,
        part_id: int | None = None,
        limit: int = 100,
    ) -> list[InventoryLogResponse]:
        query = (
            db.query(InventoryLog, Part.name)
            .join(Part, Part.id == InventoryLog.part_id)
            .filter(InventoryLog.store_id == current_user.store_id)
            .order_by(InventoryLog.id.desc())
        )
        if part_id:
            query = query.filter(InventoryLog.part_id == part_id)

        rows = query.limit(min(limit, 500)).all()
        return [
            InventoryLogResponse(
                id=log.id,
                part_id=log.part_id,
                part_name=part_name,
                type=log.type,
                quantity=log.quantity,
                before_qty=log.before_qty,
                after_qty=log.after_qty,
                ref_type=log.ref_type,
                ref_id=log.ref_id,
                remark=log.remark,
                created_at=log.created_at,
            )
            for log, part_name in rows
        ]

    @staticmethod
    def stock_in(db: Session, current_user: CurrentUser, data: StockInRequest) -> PartWithStock:
        part = InventoryService._get_part_or_404(db, current_user, data.part_id)
        inv = InventoryService.get_inventory(db, current_user.store_id, part.id)

        before = inv.quantity
        inv.quantity += data.quantity
        inv.updated_at = datetime.now(timezone.utc)

        if data.unit_cost is not None:
            total_cost = (inv.avg_cost or Decimal("0")) * before + data.unit_cost * data.quantity
            inv.avg_cost = (total_cost / inv.quantity).quantize(Decimal("0.01")) if inv.quantity else data.unit_cost
        elif part.purchase_price and inv.avg_cost is None:
            inv.avg_cost = part.purchase_price

        InventoryService._log(
            db,
            current_user.store_id,
            part.id,
            "in",
            data.quantity,
            before,
            inv.quantity,
            current_user.id,
            remark=data.remark,
        )
        db.commit()
        items = InventoryService.list_parts(db, current_user)
        return next(i for i in items if i.id == part.id)

    @staticmethod
    def lock(db: Session, current_user: CurrentUser, part_id: int, quantity: int, work_order_id: int) -> Inventory:
        part = InventoryService._get_part_or_404(db, current_user, part_id)
        inv = InventoryService.get_inventory(db, current_user.store_id, part.id)
        available = InventoryService.available_quantity(inv)
        if quantity > available:
            raise BadRequestError(f"「{part.name}」库存不足，可用 {available}，需要 {quantity}")

        before_locked = inv.locked_quantity
        inv.locked_quantity += quantity
        inv.updated_at = datetime.now(timezone.utc)

        InventoryService._log(
            db,
            current_user.store_id,
            part.id,
            "lock",
            quantity,
            before_locked,
            inv.locked_quantity,
            current_user.id,
            ref_type="work_order",
            ref_id=work_order_id,
            remark="工单锁定",
        )
        return inv

    @staticmethod
    def unlock(db: Session, current_user: CurrentUser, part_id: int, quantity: int, work_order_id: int) -> None:
        inv = InventoryService.get_inventory(db, current_user.store_id, part_id)
        unlock_qty = min(quantity, inv.locked_quantity)
        if unlock_qty <= 0:
            return

        before_locked = inv.locked_quantity
        inv.locked_quantity -= unlock_qty
        inv.updated_at = datetime.now(timezone.utc)

        InventoryService._log(
            db,
            current_user.store_id,
            part_id,
            "unlock",
            -unlock_qty,
            before_locked,
            inv.locked_quantity,
            current_user.id,
            ref_type="work_order",
            ref_id=work_order_id,
            remark="工单释放锁定",
        )

    @staticmethod
    def pick_out(db: Session, current_user: CurrentUser, part_id: int, quantity: int, work_order_id: int) -> None:
        part = InventoryService._get_part_or_404(db, current_user, part_id)
        inv = InventoryService.get_inventory(db, current_user.store_id, part.id)

        if inv.locked_quantity < quantity:
            raise BadRequestError(f"「{part.name}」锁定库存不足")
        if inv.quantity < quantity:
            raise BadRequestError(f"「{part.name}」实际库存不足")

        before_qty = inv.quantity
        inv.locked_quantity -= quantity
        inv.quantity -= quantity
        inv.updated_at = datetime.now(timezone.utc)

        InventoryService._log(
            db,
            current_user.store_id,
            part.id,
            "out",
            -quantity,
            before_qty,
            inv.quantity,
            current_user.id,
            ref_type="work_order",
            ref_id=work_order_id,
            remark="工单领料出库",
        )

    @staticmethod
    def return_stock(db: Session, current_user: CurrentUser, part_id: int, quantity: int, work_order_id: int) -> None:
        inv = InventoryService.get_inventory(db, current_user.store_id, part_id)
        before = inv.quantity
        inv.quantity += quantity
        inv.updated_at = datetime.now(timezone.utc)

        InventoryService._log(
            db,
            current_user.store_id,
            part_id,
            "in",
            quantity,
            before,
            inv.quantity,
            current_user.id,
            ref_type="work_order",
            ref_id=work_order_id,
            remark="工单退料入库",
        )

    @staticmethod
    def list_alerts(db: Session, current_user: CurrentUser) -> list[PartWithStock]:
        parts = InventoryService.list_parts(db, current_user)
        return [p for p in parts if p.is_low_stock]

    @staticmethod
    def _get_part_or_404(db: Session, current_user: CurrentUser, part_id: int) -> Part:
        part = (
            db.query(Part)
            .filter(
                Part.id == part_id,
                Part.store_id == current_user.store_id,
                Part.deleted_at.is_(None),
            )
            .first()
        )
        if not part:
            raise NotFoundError("配件不存在")
        return part
