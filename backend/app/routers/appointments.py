from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.core import Appointment
from app.models.core import User
from app.services.appointments import (
    create_appointment,
    update_appointment,
    change_appointment_status,
)

router = APIRouter(
    prefix="/api/v1/appointments",
    tags=["Appointments"],
)


class AppointmentCreate(BaseModel):
    customer_id: str | None = None
    assigned_user_id: str | None = None
    title: str
    appointment_type: str = "GENERAL"
    description: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime
    status: str = "SCHEDULED"
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    customer_id: str | None = None
    assigned_user_id: str | None = None
    title: str
    appointment_type: str = "GENERAL"
    description: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime
    notes: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: str


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    customer_id: str | None
    assigned_user_id: str | None
    title: str
    appointment_type: str
    description: str | None
    location: str | None
    start_at: datetime
    end_at: datetime
    status: str
    notes: str | None
    created_at: datetime


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = create_appointment(
        db=db,
        business_id=current_user.business_id,
        user=current_user,
        customer_id=payload.customer_id,
        assigned_user_id=payload.assigned_user_id,
        title=payload.title,
        appointment_type=payload.appointment_type,
        description=payload.description,
        location=payload.location,
        start_at=payload.start_at,
        end_at=payload.end_at,
        status_value=payload.status,
        notes=payload.notes,
    )

    db.commit()
    db.refresh(appointment)
    return appointment


@router.get(
    "",
    response_model=list[AppointmentResponse],
)
def list_appointments(
    status_filter: str | None = None,
    assigned_user_id: str | None = None,
    customer_id: str | None = None,
    from_at: datetime | None = None,
    to_at: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Appointment).filter(
        Appointment.business_id == current_user.business_id
    )

    if status_filter:
        query = query.filter(
            Appointment.status == status_filter.strip().upper()
        )

    if assigned_user_id:
        query = query.filter(
            Appointment.assigned_user_id == assigned_user_id
        )

    if customer_id:
        query = query.filter(
            Appointment.customer_id == customer_id
        )

    if from_at:
        query = query.filter(Appointment.end_at >= from_at)

    if to_at:
        query = query.filter(Appointment.start_at <= to_at)

    return query.order_by(Appointment.start_at.asc()).all()


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
)
def get_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.business_id == current_user.business_id,
        )
        .first()
    )

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return appointment


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentResponse,
)
def update(
    appointment_id: str,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.business_id == current_user.business_id,
        )
        .first()
    )

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    appointment = update_appointment(
        db=db,
        business_id=current_user.business_id,
        user=current_user,
        appointment=appointment,
        customer_id=payload.customer_id,
        assigned_user_id=payload.assigned_user_id,
        title=payload.title,
        appointment_type=payload.appointment_type,
        description=payload.description,
        location=payload.location,
        start_at=payload.start_at,
        end_at=payload.end_at,
        notes=payload.notes,
    )

    db.commit()
    db.refresh(appointment)
    return appointment


@router.patch(
    "/{appointment_id}/status",
    response_model=AppointmentResponse,
)
def update_status(
    appointment_id: str,
    payload: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.business_id == current_user.business_id,
        )
        .first()
    )

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    appointment = change_appointment_status(
        db=db,
        business_id=current_user.business_id,
        user=current_user,
        appointment=appointment,
        new_status=payload.status,
    )

    db.commit()
    db.refresh(appointment)
    return appointment
