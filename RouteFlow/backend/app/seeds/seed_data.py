"""Database seeding: demo zones, rate cards, users, agents and sample orders.

Used by both the CLI seed script (``python -m app.seeds.seed``) and the test
suite so demo data and test fixtures never drift apart.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domain.enums import (
    AgentStatus,
    FailureReason,
    OrderStatus,
    OrderType,
    PaymentType,
    UserRole,
    ZoneType,
)
from app.domain.zones import normalize_text
from app.models.rate import CodSurcharge, RateCard
from app.models.user import Customer, DeliveryAgent, User
from app.models.zone import Area, Zone
from app.schemas.order import OrderCreate
from app.services.order_service import OrderService

DEMO_PASSWORD = "Password123!"

ADMIN_EMAIL = "admin@routeflow.app"
CUSTOMER_EMAIL = "customer@routeflow.app"
AGENT_EMAIL = "agent@routeflow.app"


@dataclass
class SeededCredentials:
    admin: str
    customer: str
    agent: str
    password: str


ZONES = [
    ("CHN-01", "Chennai Central", "Chennai", ["T Nagar", "Anna Nagar", "Nungambakkam", "Kilpauk", "Egmore"]),
    ("CHN-02", "Chennai South", "Chennai", ["Velachery", "Adyar", "Guindy", "Tambaram", "Pallikaranai"]),
    ("CHN-03", "Chennai OMR", "Chennai", ["Thoraipakkam", "Sholinganallur", "Perungudi", "Navalur"]),
    ("CHN-04", "Chennai North", "Chennai", ["Royapuram", "Tondiarpet", "Perambur"]),
]

# (order_type, zone_type, [(min, max, charge), ...])
RATE_CARDS = [
    (OrderType.B2C, ZoneType.INTRA_ZONE, [(0, 5, 60), (5, 10, 90), (10, 20, 130)]),
    (OrderType.B2C, ZoneType.INTER_ZONE, [(0, 5, 80), (5, 10, 120), (10, 20, 170)]),
    (OrderType.B2B, ZoneType.INTRA_ZONE, [(0, 5, 80), (5, 10, 120), (10, 20, 180)]),
    (OrderType.B2B, ZoneType.INTER_ZONE, [(0, 5, 100), (5, 10, 150), (10, 20, 220)]),
]

COD_SURCHARGES = [(OrderType.B2B, 40), (OrderType.B2C, 30)]

# Agent seeds: (name, email, zone_index, lat, lon, max_capacity)
# The first agent uses AGENT_EMAIL so the demo agent credential is a real, assignable agent.
AGENTS = [
    ("Arjun Kumar", AGENT_EMAIL, 0, 13.0418, 80.2341, 5),
    ("Priya Nair", "priya.agent@routeflow.app", 0, 13.0640, 80.2190, 5),
    ("Ravi Shankar", "ravi.agent@routeflow.app", 1, 12.9791, 80.2210, 4),
    ("Meena Iyer", "meena.agent@routeflow.app", 1, 13.0067, 80.2570, 6),
    ("Karthik Raja", "karthik.agent@routeflow.app", 2, 12.9010, 80.2279, 5),
    ("Sneha Reddy", "sneha.agent@routeflow.app", 2, 12.9516, 80.2431, 5),
    ("Vijay Anand", "vijay.agent@routeflow.app", 3, 13.1130, 80.2870, 4),
    ("Divya Menon", "divya.agent@routeflow.app", 1, 13.0012, 80.2565, 5),
    ("Suresh Babu", "suresh.agent@routeflow.app", 0, 13.0500, 80.2400, 5),
    ("Lakshmi Priya", "lakshmi.agent@routeflow.app", 2, 12.9600, 80.2400, 5),
]

CUSTOMERS = [
    ("Ananya Sharma", "customer@routeflow.app"),
    ("Rahul Verma", "rahul@example.com"),
    ("Sadia Khan", "sadia@example.com"),
    ("Tom Fernandez", "tom@example.com"),
    ("Nisha Patel", "nisha@example.com"),
]


def _already_seeded(db: Session) -> bool:
    return db.query(User).filter(User.email == ADMIN_EMAIL).first() is not None


def seed(db: Session, *, with_orders: bool = True) -> SeededCredentials:
    """Populate the database with demo data. Idempotent: skips if already seeded."""
    creds = SeededCredentials(ADMIN_EMAIL, CUSTOMER_EMAIL, AGENT_EMAIL, DEMO_PASSWORD)
    if _already_seeded(db):
        return creds

    zones = _seed_zones(db)
    _seed_rates(db)
    admin = _seed_admin(db)
    customers = _seed_customers(db)
    _seed_agents(db, zones)
    db.commit()

    if with_orders:
        _seed_orders(db, admin, customers)
    return creds


def _seed_zones(db: Session) -> List[Zone]:
    zones: List[Zone] = []
    for code, name, city, areas in ZONES:
        zone = Zone(code=code, name=name, city=city, is_active=True)
        db.add(zone)
        db.flush()
        for area_name in areas:
            db.add(
                Area(
                    name=area_name,
                    normalized_name=normalize_text(area_name),
                    zone_id=zone.id,
                    is_active=True,
                )
            )
        zones.append(zone)
    db.flush()
    return zones


def _seed_rates(db: Session) -> None:
    for order_type, zone_type, brackets in RATE_CARDS:
        for min_w, max_w, charge in brackets:
            db.add(
                RateCard(
                    order_type=order_type,
                    zone_type=zone_type,
                    min_weight_kg=Decimal(min_w),
                    max_weight_kg=Decimal(max_w),
                    base_charge=Decimal(charge),
                    currency="INR",
                    is_active=True,
                )
            )
    for order_type, amount in COD_SURCHARGES:
        db.add(
            CodSurcharge(order_type=order_type, amount=Decimal(amount), currency="INR", is_active=True)
        )
    db.flush()


def _seed_admin(db: Session) -> User:
    admin = User(
        email=ADMIN_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        full_name="RouteFlow Admin",
        phone="+919000000001",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    return admin


def _seed_customers(db: Session) -> List[Customer]:
    customers: List[Customer] = []
    for full_name, email in CUSTOMERS:
        user = User(
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=full_name,
            phone="+919000000002",
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        db.add(user)
        db.flush()
        customer = Customer(user_id=user.id)
        db.add(customer)
        db.flush()
        customers.append(customer)
    return customers


def _seed_agents(db: Session, zones: List[Zone]) -> List[DeliveryAgent]:
    from datetime import datetime, timezone

    agents: List[DeliveryAgent] = []
    now = datetime.now(timezone.utc)
    for name, email, zone_idx, lat, lon, cap in AGENTS:
        user = User(
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=name,
            phone="+919000000003",
            role=UserRole.DELIVERY_AGENT,
            is_active=True,
        )
        db.add(user)
        db.flush()
        agent = DeliveryAgent(
            user_id=user.id,
            status=AgentStatus.AVAILABLE,
            current_zone_id=zones[zone_idx].id,
            current_latitude=lat,
            current_longitude=lon,
            last_location_update=now,
            max_active_orders=cap,
            active_orders=0,
            is_active=True,
        )
        db.add(agent)
        db.flush()
        agents.append(agent)
    return agents


def _seed_orders(db: Session, admin: User, customers: List[Customer]) -> None:
    """Create a spread of orders across statuses so dashboards look realistic."""
    service = OrderService(db)
    samples = [
        # (customer_idx, pickup, drop, dims, weight, order_type, payment, target)
        (0, "12 Gandhi Road, Velachery", "5 North Usman Road, T Nagar", (50, 40, 30), 8, OrderType.B2C, PaymentType.COD, "DELIVERED"),
        (0, "22 100 Feet Road, Velachery", "9 2nd Ave, Anna Nagar", (30, 20, 15), 3, OrderType.B2C, PaymentType.PREPAID, "OUT_FOR_DELIVERY"),
        (1, "7 Lattice Bridge Road, Adyar", "3 Sardar Patel Road, Guindy", (20, 20, 20), 4, OrderType.B2C, PaymentType.PREPAID, "IN_TRANSIT"),
        (1, "88 OMR, Thoraipakkam", "44 ECR, Sholinganallur", (60, 50, 40), 10, OrderType.B2B, PaymentType.COD, "DELIVERED"),
        (2, "10 GST Road, Tambaram", "2 Poonamallee High Road, Kilpauk", (40, 30, 30), 6, OrderType.B2B, PaymentType.PREPAID, "ASSIGNED"),
        (2, "5 Beach Road, Adyar", "17 Nungambakkam High Road, Nungambakkam", (25, 25, 25), 5, OrderType.B2C, PaymentType.COD, "FAILED"),
        (3, "3 Perungudi Main Road, Perungudi", "9 Navalur Junction, Navalur", (35, 35, 20), 7, OrderType.B2C, PaymentType.PREPAID, "CONFIRMED"),
        (3, "14 Egmore Station Road, Egmore", "6 Anna Nagar 3rd Main, Anna Nagar", (15, 15, 10), 2, OrderType.B2C, PaymentType.PREPAID, "DELIVERED"),
        (4, "21 Tondiarpet High Road, Tondiarpet", "8 Perambur Barracks Road, Perambur", (45, 40, 35), 9, OrderType.B2B, PaymentType.COD, "PENDING_CONFIRMATION"),
        (4, "2 Sholinganallur Junction, Sholinganallur", "11 Velachery Main Road, Velachery", (30, 30, 30), 6, OrderType.B2C, PaymentType.PREPAID, "DELIVERED"),
    ]

    for idx, pickup, drop, dims, weight, otype, pay, target in samples:
        data = OrderCreate(
            pickup_address=pickup,
            drop_address=drop,
            length_cm=Decimal(dims[0]),
            width_cm=Decimal(dims[1]),
            height_cm=Decimal(dims[2]),
            actual_weight_kg=Decimal(weight),
            order_type=otype,
            payment_type=pay,
            customer_id=customers[idx].id,
        )
        try:
            order = service.create_order(data, admin)
            _drive_to_status(service, order.id, admin, target)
        except Exception:
            db.rollback()


def _drive_to_status(service: OrderService, order_id: int, admin: User, target: str) -> None:
    """Advance a freshly created order to the requested demo status."""
    if target == "PENDING_CONFIRMATION":
        return
    service.confirm_order(order_id, admin)
    if target == "CONFIRMED":
        return
    service.auto_assign(order_id, admin)
    if target == "ASSIGNED":
        return
    service.update_status(order_id, OrderStatus.PICKED_UP, admin)
    service.update_status(order_id, OrderStatus.IN_TRANSIT, admin)
    if target == "IN_TRANSIT":
        return
    service.update_status(order_id, OrderStatus.OUT_FOR_DELIVERY, admin)
    if target == "OUT_FOR_DELIVERY":
        return
    if target == "DELIVERED":
        service.update_status(order_id, OrderStatus.DELIVERED, admin)
        return
    if target == "FAILED":
        service.fail_delivery(order_id, FailureReason.CUSTOMER_UNAVAILABLE, admin, notes="No response at door")
        return
