"""Reset the database and fill it with demo data.

Run from the backend folder:   uv run python -m scripts.seed
WARNING: drops and recreates every table, so ALL existing data is deleted.

Every seeded account (admin and customers) uses the password DEMO_PASSWORD.
Dates are relative to "now", so return-window cases stay valid whenever you seed.
"""

import random
import re
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.db.database import Base, SessionLocal, engine
from app.db.models import Order, OrderItem, OrderStatus, Product, Role, User

DEMO_PASSWORD = "demo1234"
ADMIN_EMAIL = "admin@example.com"
RANDOM_CUSTOMERS = 42
RANDOM_ORDERS = 300

# (sku, name, category, price in rupees). 
PRODUCTS = [
    ("MOU-001", "Wireless Mouse", "Accessories", 499),
    ("AUD-001", "Bluetooth Headphones", "Audio", 2999),
    ("ACC-001", "Laptop Stand", "Accessories", 1299),
    ("WEA-001", "Smart Watch", "Wearables", 4999),
    ("CAB-001", "USB-C Cable", "Cables", 299),
    ("KEY-001", "Mechanical Keyboard", "Accessories", 3499),
    ("MOB-001", "Phone Case", "Mobile", 399),
    ("MOB-002", "Power Bank", "Mobile", 1499),
    ("DIS-001", "LED Monitor", "Displays", 8999),
    ("CAM-001", "Webcam", "Accessories", 2499),
    ("AUD-002", "Wireless Earbuds", "Audio", 1999),
    ("AUD-003", "Bluetooth Speaker", "Audio", 2499),
    ("AUD-004", "Soundbar", "Audio", 7999),
    ("CAB-002", "HDMI Cable", "Cables", 349),
    ("CAB-003", "Lightning Cable", "Cables", 599),
    ("MOB-003", "Fast Charger 33W", "Mobile", 899),
    ("MOB-004", "Tempered Glass Screen Guard", "Mobile", 249),
    ("MOB-005", "Wireless Charging Pad", "Mobile", 1199),
    ("WEA-002", "Fitness Band", "Wearables", 2199),
    ("STO-001", "1TB External SSD", "Storage", 6999),
    ("STO-002", "64GB Pen Drive", "Storage", 549),
    ("STO-003", "128GB microSD Card", "Storage", 899),
    ("NET-001", "Wi-Fi Router", "Networking", 2799),
    ("NET-002", "Wi-Fi Range Extender", "Networking", 1599),
    ("ACC-002", "Mouse Pad XL", "Accessories", 399),
    ("ACC-003", "Laptop Backpack", "Accessories", 1799),
    ("ACC-004", "USB Hub 4-Port", "Accessories", 799),
    ("DIS-002", "Portable Monitor 15.6 inch", "Displays", 11999),
    ("ACC-005", "Ring Light", "Accessories", 1299),
    ("GAM-001", "Gaming Controller", "Gaming", 3299),
]

# (order_number, customer name, email, city, sku, quantity, status, ordered days ago, delivered days ago)
# "Out for Delivery" (ORD1008) -> shipped; "Returned" (ORD1010) -> delivered (returns live in support_requests).
ORIGINAL_ORDERS = [
    ("ORD1001", "Arun Kumar", "arun@example.com", "Chennai", "MOU-001", 2, OrderStatus.DELIVERED, 15, 12),  # outside 7-day window
    ("ORD1002", "Priya Sharma", "priya@example.com", "Mumbai", "AUD-001", 1, OrderStatus.SHIPPED, 4, None),
    ("ORD1003", "Rahul Verma", "rahul@example.com", "Delhi", "ACC-001", 1, OrderStatus.PROCESSING, 1, None),
    ("ORD1004", "Sneha Reddy", "sneha@example.com", "Hyderabad", "WEA-001", 1, OrderStatus.DELIVERED, 6, 3),  # inside window
    ("ORD1005", "Arun Kumar", "arun@example.com", "Chennai", "CAB-001", 3, OrderStatus.CANCELLED, 10, None),
    ("ORD1006", "Karthik Raja", "karthik@example.com", "Coimbatore", "KEY-001", 1, OrderStatus.SHIPPED, 3, None),
    ("ORD1007", "Divya Nair", "divya@example.com", "Kochi", "MOB-001", 2, OrderStatus.DELIVERED, 9, 6),  # inside window
    ("ORD1008", "Priya Sharma", "priya@example.com", "Mumbai", "MOB-002", 1, OrderStatus.SHIPPED, 2, None),
    ("ORD1009", "Vijay Anand", "vijay@example.com", "Bangalore", "DIS-001", 1, OrderStatus.PROCESSING, 0, None),
    ("ORD1010", "Meena Iyer", "meena@example.com", "Madurai", "CAM-001", 1, OrderStatus.DELIVERED, 14, 11),  # outside window
]

STATUS_WEIGHTS = {
    OrderStatus.DELIVERED: 50,
    OrderStatus.SHIPPED: 20,
    OrderStatus.PROCESSING: 15,
    OrderStatus.CANCELLED: 15,
}


def _tracking_number(rng: random.Random) -> str:
    return f"TRK{rng.randint(10**9, 10**10 - 1)}"


def _random_dates(rng: random.Random, status: OrderStatus, now: datetime) -> tuple[datetime, datetime | None]:
    """Return (ordered_at, delivered_at) that make sense for the status."""
    days_ago = {
        OrderStatus.PROCESSING: (0, 2),
        OrderStatus.SHIPPED: (2, 7),
        OrderStatus.DELIVERED: (4, 60),
        OrderStatus.CANCELLED: (1, 30),
    }[status]
    ordered_at = now - timedelta(days=rng.uniform(*days_ago))
    if status is not OrderStatus.DELIVERED:
        return ordered_at, None
    delivered_at = min(ordered_at + timedelta(days=rng.uniform(2, 5)), now - timedelta(hours=1))
    return ordered_at, delivered_at


def seed(db: Session, now: datetime | None = None) -> dict[str, int]:
    """Insert demo data into an empty database and return row counts."""
    now = now or datetime.now(UTC)
    rng = random.Random(42)
    fake = Faker("en_IN")
    fake.seed_instance(42)
    password_hash = hash_password(DEMO_PASSWORD)  # hashed once; every demo account shares it

    products = {sku: Product(sku=sku, name=name, category=cat, price=price) for sku, name, cat, price in PRODUCTS}
    db.add_all(products.values())

    db.add(User(name="Store Admin", email=ADMIN_EMAIL, password_hash=password_hash, role=Role.ADMIN))

    # Original customers keep their emails so the old demo questions still work.
    customers: dict[str, User] = {}
    cities: dict[str, str] = {}
    for _, name, email, city, *_ in ORIGINAL_ORDERS:
        if email not in customers:
            customers[email] = User(name=name, email=email, password_hash=password_hash)
            cities[email] = city
    for i in range(RANDOM_CUSTOMERS):
        first, last = fake.first_name(), fake.last_name()
        email = re.sub(r"[^a-z.]", "", f"{first}.{last}".lower()) + f"{i}@example.com"
        customers[email] = User(name=f"{first} {last}", email=email, password_hash=password_hash)
        cities[email] = fake.city()
    db.add_all(customers.values())

    for number, _, email, city, sku, qty, status, ordered_ago, delivered_ago in ORIGINAL_ORDERS:
        product = products[sku]
        db.add(
            Order(
                order_number=number,
                user=customers[email],
                status=status,
                total=product.price * qty,
                city=city,
                tracking_number=_tracking_number(rng) if status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED) else None,
                ordered_at=now - timedelta(days=ordered_ago, hours=2),
                delivered_at=now - timedelta(days=delivered_ago) if delivered_ago is not None else None,
                items=[OrderItem(product=product, quantity=qty, unit_price=product.price)],
            )
        )

    emails = list(customers)
    product_list = list(products.values())
    statuses, weights = list(STATUS_WEIGHTS), list(STATUS_WEIGHTS.values())
    for i in range(RANDOM_ORDERS):
        email = rng.choice(emails)
        status = rng.choices(statuses, weights)[0]
        ordered_at, delivered_at = _random_dates(rng, status, now)
        chosen = rng.sample(product_list, rng.choices([1, 2, 3], [60, 30, 10])[0])
        items = [OrderItem(product=p, quantity=rng.choices([1, 2, 3], [70, 20, 10])[0], unit_price=p.price) for p in chosen]
        db.add(
            Order(
                order_number=f"ORD{1011 + i}",
                user=customers[email],
                status=status,
                total=sum(item.quantity * item.unit_price for item in items),
                city=cities[email],
                tracking_number=_tracking_number(rng) if status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED) else None,
                ordered_at=ordered_at,
                delivered_at=delivered_at,
                items=items,
            )
        )

    db.commit()
    return {
        "users": 1 + len(customers),
        "products": len(products),
        "orders": len(ORIGINAL_ORDERS) + RANDOM_ORDERS,
    }


def main() -> None:
    print(f"Resetting database on {engine.url.host or engine.url.database} (all data will be deleted)...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        counts = seed(db)
    for table, count in counts.items():
        print(f"  {table}: {count}")
    print(f"Done. Log in with any seeded email and password '{DEMO_PASSWORD}' (admin: {ADMIN_EMAIL}).")


if __name__ == "__main__":
    main()
