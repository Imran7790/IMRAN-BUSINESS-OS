from alembic import op
import sqlalchemy as sa

revision = "cd34ef56ab78"
down_revision = "ab12cd34ef56"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "appointments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=True),
        sa.Column("assigned_user_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("appointment_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_appointments_business_id", "appointments", ["business_id"])
    op.create_index("ix_appointments_customer_id", "appointments", ["customer_id"])
    op.create_index("ix_appointments_assigned_user_id", "appointments", ["assigned_user_id"])
    op.create_index("ix_appointments_start_at", "appointments", ["start_at"])
    op.create_index("ix_appointments_end_at", "appointments", ["end_at"])
    op.create_index("ix_appointments_status", "appointments", ["status"])
    op.create_index("ix_appointments_created_at", "appointments", ["created_at"])


def downgrade():
    op.drop_index("ix_appointments_created_at", table_name="appointments")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_end_at", table_name="appointments")
    op.drop_index("ix_appointments_start_at", table_name="appointments")
    op.drop_index("ix_appointments_assigned_user_id", table_name="appointments")
    op.drop_index("ix_appointments_customer_id", table_name="appointments")
    op.drop_index("ix_appointments_business_id", table_name="appointments")
    op.drop_table("appointments")
