from alembic import op
import sqlalchemy as sa


revision = "de45ef67bc89"
down_revision = "cd34ef56ab78"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "employees",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("employee_number", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("job_title", sa.String(), nullable=False),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("branch", sa.String(), nullable=True),
        sa.Column("skills", sa.Text(), nullable=True),
        sa.Column("qualifications", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=True),
        sa.Column("hourly_rate", sa.Float(), nullable=True),
        sa.Column("commission_rate", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_index(
        "ix_employees_business_id",
        "employees",
        ["business_id"],
    )
    op.create_index(
        "ix_employees_user_id",
        "employees",
        ["user_id"],
    )
    op.create_index(
        "ix_employees_employee_number",
        "employees",
        ["employee_number"],
    )
    op.create_index(
        "ix_employees_status",
        "employees",
        ["status"],
    )
    op.create_index(
        "ix_employees_created_at",
        "employees",
        ["created_at"],
    )


def downgrade():
    op.drop_index("ix_employees_created_at", table_name="employees")
    op.drop_index("ix_employees_status", table_name="employees")
    op.drop_index("ix_employees_employee_number", table_name="employees")
    op.drop_index("ix_employees_user_id", table_name="employees")
    op.drop_index("ix_employees_business_id", table_name="employees")
    op.drop_table("employees")
