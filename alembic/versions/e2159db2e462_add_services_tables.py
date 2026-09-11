from alembic import op
import sqlalchemy as sa

revision = "e2159db2e462"
down_revision = "de45ef67bc89"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "services",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), nullable=False),
        sa.Column("service_code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("duration_minutes", sa.Float(), nullable=True),
        sa.Column("required_skills", sa.Text(), nullable=True),
        sa.Column("tax_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discount_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("warranty_days", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "service_code", name="uq_services_business_service_code"),
    )
    op.create_index("ix_services_business_id", "services", ["business_id"])
    op.create_index("ix_services_service_code", "services", ["service_code"])
    op.create_index("ix_services_category", "services", ["category"])
    op.create_index("ix_services_status", "services", ["status"])
    op.create_index("ix_services_created_at", "services", ["created_at"])
    op.create_table(
        "service_employees",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("service_id", sa.String(), nullable=False),
        sa.Column("employee_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_id", "employee_id", name="uq_service_employee"),
    )
    op.create_index("ix_service_employees_service_id", "service_employees", ["service_id"])
    op.create_index("ix_service_employees_employee_id", "service_employees", ["employee_id"])
    op.create_table(
        "service_materials",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("service_id", sa.String(), nullable=False),
        sa.Column("product_id", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_id", "product_id", name="uq_service_material"),
    )
    op.create_index("ix_service_materials_service_id", "service_materials", ["service_id"])
    op.create_index("ix_service_materials_product_id", "service_materials", ["product_id"])

def downgrade():
    op.drop_index("ix_service_materials_product_id", table_name="service_materials")
    op.drop_index("ix_service_materials_service_id", table_name="service_materials")
    op.drop_table("service_materials")
    op.drop_index("ix_service_employees_employee_id", table_name="service_employees")
    op.drop_index("ix_service_employees_service_id", table_name="service_employees")
    op.drop_table("service_employees")
    op.drop_index("ix_services_created_at", table_name="services")
    op.drop_index("ix_services_status", table_name="services")
    op.drop_index("ix_services_category", table_name="services")
    op.drop_index("ix_services_service_code", table_name="services")
    op.drop_index("ix_services_business_id", table_name="services")
    op.drop_table("services")
