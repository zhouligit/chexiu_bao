from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.dependencies import CurrentUser
from app.models.customer import Customer, Vehicle
from app.schemas.common import PageParams, PageResult
from app.schemas.customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
)


class CustomerService:
    @staticmethod
    def list_customers(db: Session, current_user: CurrentUser, params: PageParams) -> PageResult:
        query = db.query(Customer).filter(
            Customer.store_id == current_user.store_id,
            Customer.deleted_at.is_(None),
        )
        if params.keyword:
            keyword = f"%{params.keyword}%"
            query = query.filter(or_(Customer.name.ilike(keyword), Customer.phone.ilike(keyword)))

        total = query.count()
        items = (
            query.order_by(Customer.id.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
            .all()
        )
        return PageResult(
            items=[CustomerResponse.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    @staticmethod
    def create_customer(db: Session, current_user: CurrentUser, data: CustomerCreate) -> CustomerResponse:
        exists = (
            db.query(Customer)
            .filter(
                Customer.store_id == current_user.store_id,
                Customer.phone == data.phone,
                Customer.deleted_at.is_(None),
            )
            .first()
        )
        if exists:
            raise ConflictError("该手机号客户已存在")

        customer = Customer(store_id=current_user.store_id, **data.model_dump())
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return CustomerResponse.model_validate(customer)

    @staticmethod
    def get_customer(db: Session, current_user: CurrentUser, customer_id: int) -> CustomerResponse:
        customer = CustomerService._get_customer_or_404(db, current_user, customer_id)
        return CustomerResponse.model_validate(customer)

    @staticmethod
    def update_customer(
        db: Session, current_user: CurrentUser, customer_id: int, data: CustomerUpdate
    ) -> CustomerResponse:
        customer = CustomerService._get_customer_or_404(db, current_user, customer_id)
        update_data = data.model_dump(exclude_unset=True)

        if "phone" in update_data and update_data["phone"] != customer.phone:
            exists = (
                db.query(Customer)
                .filter(
                    Customer.store_id == current_user.store_id,
                    Customer.phone == update_data["phone"],
                    Customer.id != customer.id,
                    Customer.deleted_at.is_(None),
                )
                .first()
            )
            if exists:
                raise ConflictError("该手机号客户已存在")

        for key, value in update_data.items():
            setattr(customer, key, value)

        db.commit()
        db.refresh(customer)
        return CustomerResponse.model_validate(customer)

    @staticmethod
    def delete_customer(db: Session, current_user: CurrentUser, customer_id: int) -> None:
        customer = CustomerService._get_customer_or_404(db, current_user, customer_id)
        customer.deleted_at = datetime.now(UTC)
        db.commit()

    @staticmethod
    def list_vehicles(db: Session, current_user: CurrentUser, customer_id: int) -> list[VehicleResponse]:
        CustomerService._get_customer_or_404(db, current_user, customer_id)
        vehicles = (
            db.query(Vehicle)
            .filter(
                Vehicle.store_id == current_user.store_id,
                Vehicle.customer_id == customer_id,
                Vehicle.deleted_at.is_(None),
            )
            .order_by(Vehicle.id.desc())
            .all()
        )
        return [VehicleResponse.model_validate(v) for v in vehicles]

    @staticmethod
    def create_vehicle(db: Session, current_user: CurrentUser, data: VehicleCreate) -> VehicleResponse:
        CustomerService._get_customer_or_404(db, current_user, data.customer_id)
        exists = (
            db.query(Vehicle)
            .filter(
                Vehicle.store_id == current_user.store_id,
                Vehicle.plate_number == data.plate_number,
                Vehicle.deleted_at.is_(None),
            )
            .first()
        )
        if exists:
            raise ConflictError("该车牌已存在")

        vehicle = Vehicle(store_id=current_user.store_id, **data.model_dump())
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        return VehicleResponse.model_validate(vehicle)

    @staticmethod
    def update_vehicle(
        db: Session, current_user: CurrentUser, vehicle_id: int, data: VehicleUpdate
    ) -> VehicleResponse:
        vehicle = CustomerService._get_vehicle_or_404(db, current_user, vehicle_id)
        update_data = data.model_dump(exclude_unset=True)

        if "plate_number" in update_data and update_data["plate_number"] != vehicle.plate_number:
            exists = (
                db.query(Vehicle)
                .filter(
                    Vehicle.store_id == current_user.store_id,
                    Vehicle.plate_number == update_data["plate_number"],
                    Vehicle.id != vehicle.id,
                    Vehicle.deleted_at.is_(None),
                )
                .first()
            )
            if exists:
                raise ConflictError("该车牌已存在")

        for key, value in update_data.items():
            setattr(vehicle, key, value)

        db.commit()
        db.refresh(vehicle)
        return VehicleResponse.model_validate(vehicle)

    @staticmethod
    def _get_customer_or_404(db: Session, current_user: CurrentUser, customer_id: int) -> Customer:
        customer = (
            db.query(Customer)
            .filter(
                Customer.id == customer_id,
                Customer.store_id == current_user.store_id,
                Customer.deleted_at.is_(None),
            )
            .first()
        )
        if customer is None:
            raise NotFoundError("客户不存在")
        return customer

    @staticmethod
    def _get_vehicle_or_404(db: Session, current_user: CurrentUser, vehicle_id: int) -> Vehicle:
        vehicle = (
            db.query(Vehicle)
            .filter(
                Vehicle.id == vehicle_id,
                Vehicle.store_id == current_user.store_id,
                Vehicle.deleted_at.is_(None),
            )
            .first()
        )
        if vehicle is None:
            raise NotFoundError("车辆不存在")
        return vehicle
