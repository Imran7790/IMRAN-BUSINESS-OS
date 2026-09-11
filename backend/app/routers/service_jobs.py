import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import (
    ServiceJob,
    Customer,
    Service,
    Employee,
    Appointment,
)
from app.core.auth import get_current_user, require_manager
from app.services.audit import create_audit_log


router = APIRouter(
    prefix="/api/v1/service-jobs",
    tags=["service-jobs"],
)


ACTIVE_STATUSES = {
    "OPEN",
    "SCHEDULED",
    "IN_PROGRESS",
    "ON_HOLD",
}

TERMINAL_STATUSES = {
    "COMPLETED",
    "CANCELLED",
}

ALLOWED_STATUSES = ACTIVE_STATUSES | TERMINAL_STATUSES

ALLOWED_PRIORITIES = {
    "LOW",
    "NORMAL",
    "HIGH",
    "URGENT",
}

TRANSITIONS = {
    "OPEN": {"SCHEDULED", "IN_PROGRESS", "CANCELLED"},
    "SCHEDULED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"ON_HOLD", "COMPLETED", "CANCELLED"},
    "ON_HOLD": {"IN_PROGRESS", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}


class ServiceJobCreate(BaseModel):
    customer_id: str
    service_id: str
    employee_id: Optional[str] = None
    appointment_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str = "OPEN"
    priority: str = "NORMAL"
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    quoted_amount: float = 0
    actual_cost: float = 0
    notes: Optional[str] = None


class ServiceJobUpdate(BaseModel):
    customer_id: Optional[str] = None
    service_id: Optional[str] = None
    employee_id: Optional[str] = None
    appointment_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    quoted_amount: Optional[float] = None
    actual_cost: Optional[float] = None
    notes: Optional[str] = None


class StatusRequest(BaseModel):
    status: str


def _get_job(db: Session, business_id: str, job_id: str) -> ServiceJob:
    job = (
        db.query(ServiceJob)
        .filter(
            ServiceJob.id == job_id,
            ServiceJob.business_id == business_id,
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service job not found",
        )

    return job


def _get_customer(
    db: Session,
    business_id: str,
    customer_id: str,
) -> Customer:
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return customer


def _get_service(
    db: Session,
    business_id: str,
    service_id: str,
) -> Service:
    service = (
        db.query(Service)
        .filter(
            Service.id == service_id,
            Service.business_id == business_id,
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    return service


def _get_employee(
    db: Session,
    business_id: str,
    employee_id: str,
) -> Employee:
    employee = (
        db.query(Employee)
        .filter(
            Employee.id == employee_id,
            Employee.business_id == business_id,
        )
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    if employee.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee is not active",
        )

    return employee


def _get_appointment(
    db: Session,
    business_id: str,
    appointment_id: str,
) -> Appointment:
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.business_id == business_id,
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return appointment


def _validate_schedule(
    start: Optional[datetime],
    end: Optional[datetime],
) -> None:
    if start and end and end <= start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled end must be after scheduled start",
        )


def _next_job_number(
    db: Session,
    business_id: str,
) -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")

    while True:
        suffix = str(uuid.uuid4())[:8].upper()
        number = f"JOB-{date_part}-{suffix}"

        exists = (
            db.query(ServiceJob)
            .filter(ServiceJob.job_number == number)
            .first()
        )

        if not exists:
            return number

def _serialize(job: ServiceJob) -> dict:
    return {
        "id": job.id,
        "business_id": job.business_id,
        "customer_id": job.customer_id,
        "service_id": job.service_id,
        "employee_id": job.employee_id,
        "appointment_id": job.appointment_id,
        "job_number": job.job_number,
        "title": job.title,
        "description": job.description,
        "status": job.status,
        "priority": job.priority,
        "scheduled_start": job.scheduled_start,
        "scheduled_end": job.scheduled_end,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "quoted_amount": job.quoted_amount,
        "actual_cost": job.actual_cost,
        "notes": job.notes,
        "created_at": job.created_at,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_service_job(
    payload: ServiceJobCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    business_id = current_user.business_id

    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job status",
        )

    if payload.priority not in ALLOWED_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job priority",
        )

    if payload.quoted_amount < 0 or payload.actual_cost < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amounts cannot be negative",
        )

    _validate_schedule(
        payload.scheduled_start,
        payload.scheduled_end,
    )

    _get_customer(db, business_id, payload.customer_id)
    _get_service(db, business_id, payload.service_id)

    if payload.employee_id:
        _get_employee(
            db,
            business_id,
            payload.employee_id,
        )

    if payload.appointment_id:
        appointment = _get_appointment(
            db,
            business_id,
            payload.appointment_id,
        )

        if (
            appointment.customer_id
            and appointment.customer_id != payload.customer_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Appointment customer does not match job customer",
            )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    job = ServiceJob(
        business_id=business_id,
        customer_id=payload.customer_id,
        service_id=payload.service_id,
        employee_id=payload.employee_id,
        appointment_id=payload.appointment_id,
        job_number=_next_job_number(db, business_id),
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        quoted_amount=payload.quoted_amount,
        actual_cost=payload.actual_cost,
        notes=payload.notes,
    )

    if payload.status == "IN_PROGRESS":
        job.started_at = now

    if payload.status == "COMPLETED":
        job.started_at = now
        job.completed_at = now

    db.add(job)
    db.flush()

    create_audit_log(
        db,
        business_id,
        current_user.id,
        "CREATE",
        "SERVICE_JOB",
        job.id,
        f"Created service job {job.job_number}",
    )

    db.commit()
    db.refresh(job)

    return _serialize(job)


@router.get("")
def list_service_jobs(
    status_filter: Optional[str] = None,
    employee_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = (
        db.query(ServiceJob)
        .filter(
            ServiceJob.business_id == current_user.business_id
        )
    )

    if status_filter:
        if status_filter not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job status",
            )

        query = query.filter(
            ServiceJob.status == status_filter
        )

    if employee_id:
        _get_employee(
            db,
            current_user.business_id,
            employee_id,
        )
        query = query.filter(
            ServiceJob.employee_id == employee_id
        )

    if customer_id:
        _get_customer(
            db,
            current_user.business_id,
            customer_id,
        )
        query = query.filter(
            ServiceJob.customer_id == customer_id
        )

    jobs = (
        query
        .order_by(ServiceJob.created_at.desc())
        .all()
    )

    return [_serialize(job) for job in jobs]


@router.get("/{job_id}")
def get_service_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _serialize(
        _get_job(
            db,
            current_user.business_id,
            job_id,
        )
    )


@router.patch("/{job_id}")
def update_service_job(
    job_id: str,
    payload: ServiceJobUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    job = _get_job(
        db,
        current_user.business_id,
        job_id,
    )

    if job.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed or cancelled jobs cannot be edited",
        )

    if (
        payload.priority is not None
        and payload.priority not in ALLOWED_PRIORITIES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job priority",
        )

    start = (
        payload.scheduled_start
        if payload.scheduled_start is not None
        else job.scheduled_start
    )

    end = (
        payload.scheduled_end
        if payload.scheduled_end is not None
        else job.scheduled_end
    )

    _validate_schedule(start, end)

    if payload.customer_id is not None:
        _get_customer(
            db,
            current_user.business_id,
            payload.customer_id,
        )

    if payload.service_id is not None:
        _get_service(
            db,
            current_user.business_id,
            payload.service_id,
        )

    if payload.employee_id is not None:
        _get_employee(
            db,
            current_user.business_id,
            payload.employee_id,
        )

    if payload.appointment_id is not None:
        _get_appointment(
            db,
            current_user.business_id,
            payload.appointment_id,
        )

    if (
        payload.quoted_amount is not None
        and payload.quoted_amount < 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quoted amount cannot be negative",
        )

    if (
        payload.actual_cost is not None
        and payload.actual_cost < 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Actual cost cannot be negative",
        )

    for field, value in payload.model_dump(
        exclude_unset=True
    ).items():
        setattr(job, field, value)

    db.add(job)

    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "UPDATE",
        "SERVICE_JOB",
        job.id,
        f"Updated service job {job.job_number}",
    )

    db.commit()
    db.refresh(job)

    return _serialize(job)


@router.patch("/{job_id}/status")
def change_service_job_status(
    job_id: str,
    payload: StatusRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    job = _get_job(
        db,
        current_user.business_id,
        job_id,
    )

    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job status",
        )

    if payload.status == job.status:
        return _serialize(job)

    if payload.status not in TRANSITIONS[job.status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status transition: "
                f"{job.status} -> {payload.status}"
            ),
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if (
        payload.status == "IN_PROGRESS"
        and job.started_at is None
    ):
        job.started_at = now

    if payload.status == "COMPLETED":
        if job.started_at is None:
            job.started_at = now
        job.completed_at = now

    job.status = payload.status
    db.add(job)

    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "STATUS_CHANGE",
        "SERVICE_JOB",
        job.id,
        f"{job.job_number}: status changed to {payload.status}",
    )

    db.commit()
    db.refresh(job)

    return _serialize(job)


@router.post("/{job_id}/assign-employee")
def assign_employee(
    job_id: str,
    employee_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    job = _get_job(
        db,
        current_user.business_id,
        job_id,
    )

    if job.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Terminal jobs cannot be reassigned",
        )

    employee = _get_employee(
        db,
        current_user.business_id,
        employee_id,
    )

    job.employee_id = employee.id
    db.add(job)

    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "ASSIGN_EMPLOYEE",
        "SERVICE_JOB",
        job.id,
        f"{job.job_number}: assigned employee {employee.id}",
    )

    db.commit()
    db.refresh(job)

    return _serialize(job)


@router.post("/{job_id}/start")
def start_service_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    job = _get_job(
        db,
        current_user.business_id,
        job_id,
    )

    if job.status not in {
        "OPEN",
        "SCHEDULED",
        "ON_HOLD",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start job from {job.status}",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    job.status = "IN_PROGRESS"

    if job.started_at is None:
        job.started_at = now

    db.add(job)

    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "START",
        "SERVICE_JOB",
        job.id,
        f"Started service job {job.job_number}",
    )

    db.commit()
    db.refresh(job)

    return _serialize(job)


@router.post("/{job_id}/complete")
def complete_service_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    job = _get_job(
        db,
        current_user.business_id,
        job_id,
    )

    if job.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only in-progress jobs can be completed",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    job.status = "COMPLETED"
    job.completed_at = now

    if job.started_at is None:
        job.started_at = now

    db.add(job)

    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "COMPLETE",
        "SERVICE_JOB",
        job.id,
        f"Completed service job {job.job_number}",
    )

    db.commit()
    db.refresh(job)

    return _serialize(job)


@router.post("/{job_id}/cancel")
def cancel_service_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    job = _get_job(
        db,
        current_user.business_id,
        job_id,
    )

    if job.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel {job.status} job",
        )

    job.status = "CANCELLED"
    db.add(job)

    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "CANCEL",
        "SERVICE_JOB",
        job.id,
        f"Cancelled service job {job.job_number}",
    )

    db.commit()
    db.refresh(job)

    return _serialize(job)
