from alembic import op
import sqlalchemy as sa

revision = "9a1b2c3d4e5f"
down_revision = "8c91d2f4a6b7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("reorder_level", sa.Float(), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("target_quantity", sa.Float(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("products", "target_quantity")
    op.drop_column("products", "reorder_level")
