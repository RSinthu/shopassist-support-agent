"""Database tables. Money is stored as whole rupees (Integer), never float."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Role(enum.StrEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class OrderStatus(enum.StrEnum):
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class RequestType(enum.StrEnum):
    CANCEL = "cancel"
    RETURN = "return"
    REFUND = "refund"


class RequestStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def _enum_column(enum_cls: type[enum.Enum]) -> Enum:
    # Stored as VARCHAR + CHECK (not a native Postgres enum) using the lowercase values,
    # so it behaves the same in Postgres and in the SQLite test database.
    return Enum(
        enum_cls,
        native_enum=False,
        create_constraint=True,  # the database itself rejects values outside the enum
        length=20,
        values_callable=lambda e: [m.value for m in e],
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum_column(Role), default=Role.CUSTOMER)
    created_at: Mapped[datetime] = _created_at()

    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("price >= 0", name="ck_products_price"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    price: Mapped[int]


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(_enum_column(OrderStatus), default=OrderStatus.PROCESSING)
    total: Mapped[int]
    city: Mapped[str] = mapped_column(String(100))
    tracking_number: Mapped[str | None] = mapped_column(String(50))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_items_quantity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    unit_price: Mapped[int]  # price paid at order time, independent of later price changes

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class SupportRequest(Base):
    __tablename__ = "support_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[RequestType] = mapped_column(_enum_column(RequestType))
    status: Mapped[RequestStatus] = mapped_column(_enum_column(RequestStatus), default=RequestStatus.PENDING)
    amount: Mapped[int | None]
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()

    order: Mapped[Order] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # None = system action
    action: Mapped[str] = mapped_column(String(50))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = _created_at()
