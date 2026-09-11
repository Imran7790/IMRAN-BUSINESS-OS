from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.core import Appointment, Customer, User
from app.services.audit import create_audit_log


ACTIVE_STATUSES = {"SCHEDULED", "CONFIRMED"}
ALL_STATUSES = {"SCHEDULED", "CONFIRMED", "COMPLETED", "CANCELLED", "NO_SHOW"}


def validate_appointment_window(start_at: datetime, end_at: datetime):
    if end_at <= start_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_at must be later than start_at",
        )


def validate_customer(
    db: Session,
    business_id: str,
    customer_id: str | None,
):
    if customer_id is None:
        return None

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return customer


def validate_assigned_user(
    db: Session,
    business_id: str,
    assigned_user_id: str | None,
):
    if assigned_user_id is None:
        return None

    user = (
        db.query(User)
        .filter(
            User.id == assigned_user_id,
            User.business_id == business_id,
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user not found",
        )

    return user


def check_appointment_conflict(
    db: Session,
    *,
    business_id: str,
    assigned_user_id: str | None,
    start_at: datetime,
    end_at: datetime,
    exclude_appointment_id: str | None = None,
):
    if assigned_user_id is None:
        return None

    query = (
        db.query(Appointment)
        .filter(
            Appointment.business_id == business_id,
            Appointment.assigned_user_id == assigned_user_id,
            Appointment.status.in_(ACTIVE_STATUSES),
            Appointment.start_at < end_at,
            Appointment.end_at > start_at,
        )
    )

    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)

    return query.first()


def create_appointment(
    db: Session,
    *,
    business_id: str,
    user: User,
    customer_id: str | None,
    assigned_user_id: str | None,
    title: str,
    appointment_type: str,
    description: str | None,
    location: str | None,
    start_at: datetime,
    end_at: datetime,
    status_value: str = "SCHEDULED",
    notes: str | None = None,
):
    title = title.strip()
    appointment_type = appointment_type.strip().upper()
    status_value = status_value.strip().upper()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title is required",
        )

    validate_appointment_window(start_at, end_at)

    if status_value not in ALL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid appointment status",
        )

    validate_customer(db, business_id, customer_id)
    validate_assigned_user(db, business_id, assigned_user_id)

    conflict = check_appointment_conflict(
        db,
        business_id=business_id,
        assigned_user_id=assigned_user_id,
        start_at=start_at,
        end_at=end_at,
    )

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assigned user already has an overlapping appointment",
        )

    appointment = Appointment(
        business_id=business_id,
        customer_id=customer_id,
        assigned_user_id=assigned_user_id,
        title=title,
        appointment_type=appointment_type or "GENERAL",
        description=description,
        location=location,
        start_at=start_at,
        end_at=end_at,
        status=status_value,
        notes=notes,
    )

    db.add(appointment)
    db.flush()

    create_audit_log(
        db=db,
        business_id=business_id,
        user_id=user.id,
        action="CREATE",
        entity_type="APPOINTMENT",
        entity_id=appointment.id,
        details=(
            f"title={appointment.title};"
            f"customer_id={customer_id};"
            f"assigned_user_id={assigned_user_id};"
            f"start_at={start_at.isoformat()};"
            f"end_at={end_at.isoformat()};"
            f"status={status_value}"
        ),
    )

    return appointment


def update_appointment(
    db: Session,
    *,
    business_id: str,
    user: User,
    appointment: Appointment,
    customer_id: str | None,
    assigned_user_id: str | None,
    title: str,
    appointment_type: str,
    description: str | None,
    location: str | None,
    start_at: datetime,
    end_at: datetime,
    notes: str | None,
):
    validate_appointment_window(start_at, end_at)
    validate_customer(db, business_id, customer_id)
    validate_assigned_user(db, business_id, assigned_user_id)

    conflict = check_appointment_conflict(
        db,
        business_id=business_id,
        assigned_user_id=assigned_user_id,
        start_at=start_at,
        end_at=end_at,
        exclude_appointment_id=appointment.id,
    )

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assigned user already has an overlapping appointment",
        )

    appointment.customer_id = customer_id
    appointment.assigned_user_id = assigned_user_id
    appointment.title = title.strip()
    appointment.appointment_type = appointment_type.strip().upper() or "GENERAL"
    appointment.description = description
    appointment.location = location
    appointment.start_at = start_at
    appointment.end_at = end_at
    appointment.notes = notes

    db.flush()

    create_audit_log(
        db=db,
        business_id=business_id,
        user_id=user.id,
        action="UPDATE",
        entity_type="APPOINTMENT",
        entity_id=appointment.id,
        details=(
            f"title={appointment.title};"
            f"customer_id={customer_id};"
            f"assigned_user_id={assigned_user_id};"
            f"start_at={start_at.isoformat()};"
            f"end_at={end_at.isoformat()}"
        ),
    )

    return appointment


def change_appointment_status(
    db: Session,
    *,
    business_id: str,
    user: User,
    appointment: Appointment,
    new_status: str,
):
    new_status = new_status.strip().upper()

    if new_status not in ALL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid appointment status",
        )

    old_status = appointment.status
    appointment.status = new_status

    db.flush()

    create_audit_log(
        db=db,
        business_id=business_id,
        user_id=user.id,
        action="UPDATE",
        entity_type="APPOINTMENT",
        entity_id=appointment.id,
        details=f"status_change={old_status}->{new_status}",
    )

    return appointment
