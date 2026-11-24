from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.models import Order, OrderItem, OrderStatus, Product, Role, User


def make_user(db, email="arun@example.com"):
    user = User(name="Arun Kumar", email=email, password_hash="x")
    db.add(user)
    db.commit()
    return user


def test_order_with_items_reads_back_through_relationships(db):
    user = make_user(db)
    mouse = Product(sku="MOU-001", name="Wireless Mouse", category="Accessories", price=499)
    order = Order(
        order_number="ORD1001",
        user=user,
        total=998,
        city="Chennai",
        ordered_at=datetime.now(UTC),
        items=[OrderItem(product=mouse, quantity=2, unit_price=499)],
    )
    db.add(order)
    db.commit()

    saved = db.get(User, user.id)
    assert saved.role is Role.CUSTOMER
    assert saved.orders[0].status is OrderStatus.PROCESSING
    assert saved.orders[0].items[0].product.name == "Wireless Mouse"


def test_duplicate_email_is_rejected(db):
    make_user(db)
    with pytest.raises(IntegrityError):
        make_user(db)


def test_enums_are_stored_as_lowercase_values(db):
    make_user(db)
    stored_role = db.execute(text("SELECT role FROM users")).scalar_one()
    assert stored_role == "customer"


def test_database_rejects_unknown_enum_value(db):
    with pytest.raises(IntegrityError):
        db.execute(text("INSERT INTO users (name, email, password_hash, role) VALUES ('X', 'x@x.com', 'x', 'superuser')"))
