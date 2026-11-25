"""Checks that the seed data is consistent. Runs on in-memory SQLite, never on Neon."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.db.models import Order, OrderStatus, Role, User
from scripts.seed import seed

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)  # SQLite drops timezone info


@pytest.fixture
def orders(db):
    seed(db, now=NOW)
    return db.scalars(select(Order)).all()


def test_row_counts(db, orders):
    assert db.scalar(select(func.count()).select_from(User)) == 51
    assert len(orders) == 310
    assert db.scalar(select(func.count()).where(User.role == Role.ADMIN)) == 1


def test_totals_match_items(orders):
    for order in orders:
        assert order.total == sum(i.quantity * i.unit_price for i in order.items), order.order_number


def test_dates_and_tracking_match_status(orders):
    for order in orders:
        if order.status is OrderStatus.DELIVERED:
            assert order.delivered_at is not None and order.tracking_number
            assert as_utc(order.ordered_at) < as_utc(order.delivered_at) <= NOW
        elif order.status is OrderStatus.SHIPPED:
            assert order.delivered_at is None and order.tracking_number
        else:
            assert order.delivered_at is None and order.tracking_number is None
        assert as_utc(order.ordered_at) <= NOW


def test_return_window_examples(orders):
    by_number = {o.order_number: o for o in orders}
    assert (NOW - as_utc(by_number["ORD1004"].delivered_at)).days < 7  # inside window
    assert (NOW - as_utc(by_number["ORD1001"].delivered_at)).days > 7  # outside window
