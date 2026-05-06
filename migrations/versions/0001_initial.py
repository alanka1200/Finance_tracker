"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-05

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === ENUM типы ===
    op.execute("CREATE TYPE category_kind AS ENUM ('income', 'expense')")
    op.execute("CREATE TYPE transaction_kind AS ENUM ('income', 'expense')")
    op.execute("CREATE TYPE goal_status AS ENUM ('active', 'completed', 'archived')")
    op.execute("CREATE TYPE goal_priority AS ENUM ('1', '2', '3')")
    op.execute(
        "CREATE TYPE investment_type AS ENUM "
        "('stock', 'bond', 'crypto', 'deposit', 'real_estate', 'other')"
    )
    op.execute("CREATE TYPE referral_status AS ENUM ('pending', 'confirmed')")

    # === users ===
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(128), nullable=True),
        sa.Column("last_name", sa.String(128), nullable=True),
        sa.Column("language_code", sa.String(8), nullable=True),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Europe/Moscow"),
        sa.Column("referral_code", sa.String(16), nullable=True),
        sa.Column("referred_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
        sa.UniqueConstraint("referral_code", name="uq_users_referral_code"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])
    op.create_index("ix_users_referral_code", "users", ["referral_code"])
    op.create_index("ix_users_referred_by_user_id", "users", ["referred_by_user_id"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    op.create_index(
        "ix_users_telegram_id_active",
        "users",
        ["telegram_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # === categories ===
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("kind", sa.Enum("income", "expense", name="category_kind", create_type=False), nullable=False),
        sa.Column("icon", sa.String(8), nullable=False, server_default="💰"),
        sa.Column("color", sa.String(7), nullable=False, server_default="#40a7e3"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.create_index("ix_categories_kind", "categories", ["kind"])
    op.create_index("ix_categories_deleted_at", "categories", ["deleted_at"])
    op.create_index(
        "ix_categories_user_kind_active",
        "categories",
        ["user_id", "kind"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # === transactions ===
    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.BigInteger(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.Enum("income", "expense", name="transaction_kind", create_type=False), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="RUB"),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("tags", sa.String(256), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_kind", "transactions", ["kind"])
    op.create_index("ix_transactions_occurred_at", "transactions", ["occurred_at"])
    op.create_index("ix_transactions_deleted_at", "transactions", ["deleted_at"])
    # Главные композитные индексы для быстрых запросов
    op.execute(
        "CREATE INDEX ix_transactions_user_date ON transactions "
        "USING btree (user_id, occurred_at DESC) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_transactions_user_category ON transactions "
        "USING btree (user_id, category_id, occurred_at DESC) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_transactions_user_kind ON transactions "
        "USING btree (user_id, kind, occurred_at DESC) WHERE deleted_at IS NULL"
    )

    # === goals ===
    op.create_table(
        "goals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("target_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("current_amount", sa.Numeric(19, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="RUB"),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category_label", sa.String(64), nullable=True),
        sa.Column("icon", sa.String(8), nullable=False, server_default="🎯"),
        sa.Column(
            "priority",
            sa.Enum("1", "2", "3", name="goal_priority", create_type=False),
            nullable=False,
            server_default="2",
        ),
        sa.Column(
            "status",
            sa.Enum("active", "completed", "archived", name="goal_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index("ix_goals_status", "goals", ["status"])
    op.create_index("ix_goals_deleted_at", "goals", ["deleted_at"])
    op.execute(
        "CREATE INDEX ix_goals_user_status_active ON goals "
        "(user_id, status) WHERE deleted_at IS NULL"
    )

    # === investments ===
    op.create_table(
        "investments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "stock", "bond", "crypto", "deposit", "real_estate", "other",
                name="investment_type", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("ticker", sa.String(32), nullable=True),
        sa.Column("purchase_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("quantity", sa.Numeric(19, 8), nullable=False, server_default="1"),
        sa.Column("purchase_price", sa.Numeric(19, 8), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("current_price", sa.Numeric(19, 8), nullable=True),
        sa.Column("current_value", sa.Numeric(19, 4), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="RUB"),
        sa.Column("notes", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_investments_user_id", "investments", ["user_id"])
    op.create_index("ix_investments_ticker", "investments", ["ticker"])
    op.create_index("ix_investments_deleted_at", "investments", ["deleted_at"])
    op.execute(
        "CREATE INDEX ix_investments_user_active ON investments "
        "(user_id) WHERE deleted_at IS NULL"
    )

    # === referrals ===
    op.create_table(
        "referrals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("referrer_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("referred_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "confirmed", name="referral_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("referred_user_id", name="uq_referrals_referred_user_id"),
    )
    op.create_index("ix_referrals_referrer_user_id", "referrals", ["referrer_user_id"])
    op.create_index("ix_referrals_referrer_status", "referrals", ["referrer_user_id", "status"])


def downgrade() -> None:
    op.drop_table("referrals")
    op.drop_table("investments")
    op.drop_table("goals")
    op.drop_table("transactions")
    op.drop_table("categories")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS referral_status")
    op.execute("DROP TYPE IF EXISTS investment_type")
    op.execute("DROP TYPE IF EXISTS goal_priority")
    op.execute("DROP TYPE IF EXISTS goal_status")
    op.execute("DROP TYPE IF EXISTS transaction_kind")
    op.execute("DROP TYPE IF EXISTS category_kind")
