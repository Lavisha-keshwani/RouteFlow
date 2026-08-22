"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts(),
    )
    op.create_index("ix_zones_code", "zones", ["code"], unique=True)

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("default_pickup_address", sa.String(500)),
        *_ts(),
    )

    op.create_table(
        "delivery_agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_zone_id", sa.Integer(), sa.ForeignKey("zones.id", ondelete="SET NULL")),
        sa.Column("current_latitude", sa.Float()),
        sa.Column("current_longitude", sa.Float()),
        sa.Column("last_location_update", sa.DateTime(timezone=True)),
        sa.Column("max_active_orders", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("active_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("max_active_orders > 0", name="ck_agent_capacity_positive"),
        sa.CheckConstraint("active_orders >= 0", name="ck_agent_active_nonneg"),
        *_ts(),
    )
    op.create_index("ix_agents_status", "delivery_agents", ["status"])

    op.create_table(
        "areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("normalized_name", sa.String(150), nullable=False),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("normalized_name", name="uq_area_normalized_name"),
        *_ts(),
    )
    op.create_index("ix_areas_normalized_name", "areas", ["normalized_name"])
    op.create_index("ix_areas_zone_id", "areas", ["zone_id"])

    op.create_table(
        "rate_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_type", sa.String(10), nullable=False),
        sa.Column("zone_type", sa.String(15), nullable=False),
        sa.Column("min_weight_kg", sa.Numeric(8, 3), nullable=False),
        sa.Column("max_weight_kg", sa.Numeric(8, 3), nullable=False),
        sa.Column("base_charge", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("min_weight_kg >= 0", name="ck_rate_min_nonneg"),
        sa.CheckConstraint("max_weight_kg > min_weight_kg", name="ck_rate_range_valid"),
        sa.CheckConstraint("base_charge >= 0", name="ck_rate_charge_nonneg"),
        *_ts(),
    )
    op.create_index("ix_rate_lookup", "rate_cards", ["order_type", "zone_type", "is_active"])

    op.create_table(
        "cod_surcharges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_type", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("order_type", name="uq_cod_order_type"),
        sa.CheckConstraint("amount >= 0", name="ck_cod_amount_nonneg"),
        *_ts(),
    )

    op.create_table(
        "agent_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("delivery_agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_locations_agent_time", "agent_locations", ["agent_id", "recorded_at"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_number", sa.String(30), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_agent_id", sa.Integer(), sa.ForeignKey("delivery_agents.id", ondelete="SET NULL")),
        sa.Column("pickup_address", sa.String(500), nullable=False),
        sa.Column("drop_address", sa.String(500), nullable=False),
        sa.Column("pickup_area_id", sa.Integer(), sa.ForeignKey("areas.id")),
        sa.Column("drop_area_id", sa.Integer(), sa.ForeignKey("areas.id")),
        sa.Column("pickup_zone_id", sa.Integer(), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("drop_zone_id", sa.Integer(), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("pickup_latitude", sa.Float()),
        sa.Column("pickup_longitude", sa.Float()),
        sa.Column("drop_latitude", sa.Float()),
        sa.Column("drop_longitude", sa.Float()),
        sa.Column("order_type", sa.String(10), nullable=False),
        sa.Column("payment_type", sa.String(10), nullable=False),
        sa.Column("zone_type", sa.String(15), nullable=False),
        sa.Column("status", sa.String(25), nullable=False),
        sa.Column("chargeable_weight_kg", sa.Numeric(8, 3), nullable=False),
        sa.Column("base_charge", sa.Numeric(12, 2), nullable=False),
        sa.Column("cod_surcharge", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_charge", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("rate_card_id", sa.Integer(), sa.ForeignKey("rate_cards.id")),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("total_charge >= 0", name="ck_order_total_nonneg"),
        *_ts(),
    )
    op.create_index("ix_orders_order_number", "orders", ["order_number"], unique=True)
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_customer", "orders", ["customer_id"])
    op.create_index("ix_orders_agent", "orders", ["assigned_agent_id"])
    op.create_index("ix_orders_pickup_zone", "orders", ["pickup_zone_id"])
    op.create_index("ix_orders_drop_zone", "orders", ["drop_zone_id"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("length_cm", sa.Numeric(8, 2), nullable=False),
        sa.Column("width_cm", sa.Numeric(8, 2), nullable=False),
        sa.Column("height_cm", sa.Numeric(8, 2), nullable=False),
        sa.Column("actual_weight_kg", sa.Numeric(8, 3), nullable=False),
        sa.Column("volumetric_weight_kg", sa.Numeric(8, 3), nullable=False),
        sa.Column("chargeable_weight_kg", sa.Numeric(8, 3), nullable=False),
        sa.CheckConstraint("length_cm > 0 AND width_cm > 0 AND height_cm > 0", name="ck_pkg_dims_positive"),
        sa.CheckConstraint("actual_weight_kg > 0", name="ck_pkg_actual_positive"),
        *_ts(),
    )

    op.create_table(
        "delivery_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("delivery_agents.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(15), nullable=False),
        sa.Column("scheduled_date", sa.Date()),
        sa.Column("time_window", sa.String(50)),
        sa.Column("failure_reason", sa.String(25)),
        sa.Column("notes", sa.Text()),
        sa.Column("reschedule_reason", sa.Text()),
        sa.Column("assignment_score", sa.Float()),
        sa.Column("assignment_metadata", sa.JSON()),
        sa.UniqueConstraint("order_id", "attempt_number", name="uq_attempt_order_number"),
        *_ts(),
    )
    op.create_index("ix_attempts_order", "delivery_attempts", ["order_id"])
    op.create_index("ix_attempts_agent", "delivery_attempts", ["agent_id"])

    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_status", sa.String(25)),
        sa.Column("new_status", sa.String(25), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("actor_role", sa.String(20)),
        sa.Column("reason", sa.Text()),
        sa.Column("metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_status_history_order", "order_status_history", ["order_id", "created_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE")),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("event_type", sa.String(25), nullable=False),
        sa.Column("subject", sa.String(255)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        *_ts(),
    )
    op.create_index("ix_notifications_order", "notifications", ["order_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("response_order_id", sa.Integer(), sa.ForeignKey("orders.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key", "endpoint", name="uq_idempotency_key_endpoint"),
    )
    op.create_index("ix_idempotency_keys_key", "idempotency_keys", ["key"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("actor_role", sa.String(20)),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(50)),
        sa.Column("old_value", sa.JSON()),
        sa.Column("new_value", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])


def downgrade() -> None:
    for table in [
        "audit_logs",
        "idempotency_keys",
        "notifications",
        "order_status_history",
        "delivery_attempts",
        "packages",
        "orders",
        "agent_locations",
        "cod_surcharges",
        "rate_cards",
        "areas",
        "delivery_agents",
        "customers",
        "zones",
        "users",
    ]:
        op.drop_table(table)
