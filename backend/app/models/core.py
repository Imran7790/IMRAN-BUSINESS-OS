from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Column,
    Boolean,
    String,
    Float,
    ForeignKey,
    DateTime,
    Date,
    Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    country_code = Column(String, nullable=False)
    currency_code = Column(String, nullable=False)
    timezone = Column(String, nullable=False)
    language_code = Column(String, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    users = relationship(
        "User",
        back_populates="business"
    )

    customers = relationship(
        "Customer",
        back_populates="business"
    )

    suppliers = relationship(
        "Supplier",
        back_populates="business"
    )

    products = relationship(
        "Product",
        back_populates="business"
    )


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False
    )
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    business = relationship(
        "Business",
        back_populates="users"
    )


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False
    )
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    address = Column(String)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    business = relationship(
        "Business",
        back_populates="customers"
    )


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False
    )
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    address = Column(String)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    business = relationship(
        "Business",
        back_populates="suppliers"
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False
    )
    name = Column(String, nullable=False)
    sku = Column(String)
    type = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    cost = Column(Float)
    quantity = Column(Float, nullable=False, default=0)
    reorder_level = Column(Float, nullable=False, default=0)
    target_quantity = Column(Float, nullable=False, default=0)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    business = relationship(
        "Business",
        back_populates="products"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False
    )
    customer_id = Column(
        String,
        ForeignKey("customers.id"),
        nullable=True
    )
    type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency_code = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )


class Sale(Base):
    __tablename__ = "sales"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )
    customer_id = Column(
        String,
        ForeignKey("customers.id"),
        nullable=True,
        index=True
    )
    currency_code = Column(
        String,
        nullable=False
    )
    subtotal = Column(
        Float,
        nullable=False
    )
    total = Column(
        Float,
        nullable=False
    )
    status = Column(
        String,
        nullable=False,
        default="COMPLETED"
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True
    )


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    sale_id = Column(
        String,
        ForeignKey("sales.id"),
        nullable=False,
        index=True
    )
    product_id = Column(
        String,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )
    quantity = Column(
        Float,
        nullable=False
    )
    unit_price = Column(
        Float,
        nullable=False
    )
    line_total = Column(
        Float,
        nullable=False
    )


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )
    supplier_id = Column(
        String,
        ForeignKey("suppliers.id"),
        nullable=True,
        index=True
    )
    currency_code = Column(
        String,
        nullable=False
    )
    subtotal = Column(
        Float,
        nullable=False
    )
    total = Column(
        Float,
        nullable=False
    )
    status = Column(
        String,
        nullable=False,
        default="COMPLETED"
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True
    )


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    purchase_id = Column(
        String,
        ForeignKey("purchases.id"),
        nullable=False,
        index=True
    )
    product_id = Column(
        String,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )
    quantity = Column(
        Float,
        nullable=False
    )
    unit_cost = Column(
        Float,
        nullable=False
    )
    line_total = Column(
        Float,
        nullable=False
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    notification_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="INFO", index=True)
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True,
    )

    business = relationship("Business")
    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )
    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=True, index=True)
    details = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True
    )

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )
    product_id = Column(
        String,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )
    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    movement_type = Column(
        String,
        nullable=False,
        index=True
    )
    quantity = Column(
        Float,
        nullable=False
    )
    quantity_before = Column(
        Float,
        nullable=False
    )
    quantity_after = Column(
        Float,
        nullable=False
    )
    reference_type = Column(
        String,
        nullable=True
    )
    reference_id = Column(
        String,
        nullable=True,
        index=True
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True
    )

# ============================================================
# INVOICES
# ============================================================

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    customer_id = Column(
        String,
        ForeignKey("customers.id"),
        nullable=True,
        index=True
    )

    invoice_number = Column(
        String,
        nullable=False,
        unique=True,
        index=True
    )

    currency_code = Column(
        String,
        nullable=False
    )

    subtotal = Column(
        Float,
        nullable=False
    )

    discount = Column(
        Float,
        nullable=False,
        default=0
    )

    tax = Column(
        Float,
        nullable=False,
        default=0
    )

    total = Column(
        Float,
        nullable=False
    )

    status = Column(
        String,
        nullable=False,
        default="DRAFT",
        index=True
    )

    due_date = Column(
        Date,
        nullable=True
    )

    issued_at = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    invoice_id = Column(
        String,
        ForeignKey("invoices.id"),
        nullable=False,
        index=True
    )

    product_id = Column(
        String,
        ForeignKey("products.id"),
        nullable=True,
        index=True
    )

    description = Column(
        String,
        nullable=False
    )

    quantity = Column(
        Float,
        nullable=False
    )

    unit_price = Column(
        Float,
        nullable=False
    )

    line_total = Column(
        Float,
        nullable=False
    )

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, index=True)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency_code = Column(String, nullable=False)
    payment_method = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    paid_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

# ============================================================
# QUOTATIONS
# ============================================================

class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    business_id = Column(
        String,
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    customer_id = Column(
        String,
        ForeignKey("customers.id"),
        nullable=True,
        index=True
    )

    quotation_number = Column(
        String,
        nullable=False,
        unique=True,
        index=True
    )

    currency_code = Column(
        String,
        nullable=False
    )

    subtotal = Column(
        Float,
        nullable=False
    )

    discount = Column(
        Float,
        nullable=False,
        default=0
    )

    tax = Column(
        Float,
        nullable=False,
        default=0
    )

    total = Column(
        Float,
        nullable=False
    )

    status = Column(
        String,
        nullable=False,
        default="DRAFT",
        index=True
    )

    valid_until = Column(
        Date,
        nullable=True
    )

    notes = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True
    )


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    quotation_id = Column(
        String,
        ForeignKey("quotations.id"),
        nullable=False,
        index=True
    )

    product_id = Column(
        String,
        ForeignKey("products.id"),
        nullable=True,
        index=True
    )

    description = Column(
        String,
        nullable=False
    )

    quantity = Column(
        Float,
        nullable=False
    )

    unit_price = Column(
        Float,
        nullable=False
    )

    line_total = Column(
        Float,
        nullable=False
    )

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=True, index=True)
    assigned_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    appointment_type = Column(String, nullable=False, default="GENERAL")
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    start_at = Column(DateTime, nullable=False, index=True)
    end_at = Column(DateTime, nullable=False, index=True)
    status = Column(String, nullable=False, default="SCHEDULED", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True,
    )

    business = relationship("Business")
    customer = relationship("Customer")
    assigned_user = relationship("User")



class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, unique=True, index=True)
    employee_number = Column(String, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    job_title = Column(String, nullable=False)
    department = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    skills = Column(Text, nullable=True)
    qualifications = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE", index=True)
    hire_date = Column(Date, nullable=True)
    hourly_rate = Column(Float, nullable=True)
    commission_rate = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True,
    )

    business = relationship("Business")
    user = relationship("User")


class Service(Base):
    __tablename__ = "services"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, index=True)
    service_code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True, index=True)
    price = Column(Float, nullable=False, default=0)
    cost = Column(Float, nullable=False, default=0)
    duration_minutes = Column(Float, nullable=True)
    required_skills = Column(Text, nullable=True)
    tax_rate = Column(Float, nullable=False, default=0)
    discount_rate = Column(Float, nullable=False, default=0)
    warranty_days = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True,
    )

    business = relationship("Business")


class ServiceEmployee(Base):
    __tablename__ = "service_employees"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    service_id = Column(String, ForeignKey("services.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )

    service = relationship("Service")
    employee = relationship("Employee")


class ServiceMaterial(Base):
    __tablename__ = "service_materials"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    service_id = Column(String, ForeignKey("services.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )

    service = relationship("Service")
    product = relationship("Product")


class ServiceJob(Base):
    __tablename__ = "service_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False, index=True)
    service_id = Column(String, ForeignKey("services.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=True, index=True)
    appointment_id = Column(String, ForeignKey("appointments.id"), nullable=True, index=True)
    job_number = Column(String, nullable=False, unique=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="OPEN", index=True)
    priority = Column(String, nullable=False, default="NORMAL", index=True)
    scheduled_start = Column(DateTime, nullable=True, index=True)
    scheduled_end = Column(DateTime, nullable=True, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    quoted_amount = Column(Float, nullable=False, default=0)
    actual_cost = Column(Float, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True,
    )

    business = relationship("Business")
    customer = relationship("Customer")
    service = relationship("Service")
    employee = relationship("Employee")
    appointment = relationship("Appointment")

