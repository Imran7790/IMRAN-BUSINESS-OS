"""add quotation tables
from typing import Sequence, Union

Revision ID: 8c91d2f4a6b7
Revises: 7eabf50057ab
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c91d2f4a6b7"
down_revision: Union[str, Sequence[str], None] = "7eabf50057ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=True),
        sa.Column("quotation_number", sa.String(), nullable=False),
        sa.Column("currency_code", sa.String(), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("discount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quotation_number"),
    )

    op.create_index(
        "ix_quotations_business_id",
        "quotations",
        ["business_id"],
    )
    op.create_index(
        "ix_quotations_customer_id",
        "quotations",
        ["customer_id"],
    )
    op.create_index(
        "ix_quotations_quotation_number",
        "quotations",
        ["quotation_number"],
        unique=False,
    )
    op.create_index(
        "ix_quotations_status",
        "quotations",
        ["status"],
    )
    op.create_index(
        "ix_quotations_created_at",
        "quotations",
        ["created_at"],
    )

    op.create_table(
        "quotation_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("quotation_id", sa.String(), nullable=False),
        sa.Column("product_id", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("line_total", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_quotation_items_quotation_id",
        "quotation_items",
        ["quotation_id"],
    )
    op.create_index(
        "ix_quotation_items_product_id",
        "quotation_items",
        ["product_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_quotation_items_product_id",
        table_name="quotation_items",
    )
    op.drop_index(
        "ix_quotation_items_quotation_id",
        table_name="quotation_items",
    )
    op.drop_table("quotation_items")

    op.drop_index(
        "ix_quotations_created_at",
        table_name="quotations",
    )
    op.drop_index(
        "ix_quotations_status",
        table_name="quotations",
    )
    op.drop_index(
        "ix_quotations_quotation_number",
        table_name="quotations",
    )
    op.drop_index(
        "ix_quotations_customer_id",
        table_name="quotations",
    )
    op.drop_index(
        "ix_quotations_business_id",
        table_name="quotations",
    )
    op.drop_table("quotations")
