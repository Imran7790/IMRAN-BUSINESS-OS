from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.core import Business, Employee, User
from app.services.audit import create_audit_log


EMPLOYEE_STATUSES = {"ACTIVE", "INACTIVE", "ON_LEAVE", "TERMINATED"}


def _get_employee(db: Session, business_id: str, employee_id: str) -> Employee:
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

    return employee


def _validate_user_link(
    db: Session,
    business_id: str,
    user_id: Optional[str],
):
    if user_id is None:
        return None

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.business_id == business_id,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to this business",
        )

    existing = (
        db.query(Employee)
        .filter(
            Employee.user_id == user_id,
            Employee.business_id == business_id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already linked to an employee",
        )

    return user


def _validate_employee_number(
    db: Session,
    business_id: str,
    employee_number: str,
    exclude_employee_id: Optional[str] = None,
):
    query = db.query(Employee).filter(
        Employee.business_id == business_id,
        Employee.employee_number == employee_number,
    )

    if exclude_employee_id:
        query = query.filter(Employee.id != exclude_employee_id)

    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee number already exists in this business",
        )


def create_employee(
    db: Session,
    business_id: str,
    actor_user_id: str,
    employee_number: str,
    full_name: str,
    job_title: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    department: Optional[str] = None,
    branch: Optional[str] = None,
    skills: Optional[str] = None,
    qualifications: Optional[str] = None,
    status_value: str = "ACTIVE",
    hire_date: Optional[date] = None,
    hourly_rate: Optional[float] = None,
    commission_rate: Optional[float] = None,
    notes: Optional[str] = None,
    user_id: Optional[str] = None,
):
    if status_value not in EMPLOYEE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid employee status",
        )

    _validate_employee_number(
        db,
        business_id,
        employee_number,
    )

    _validate_user_link(
        db,
        business_id,
        user_id,
    )

    employee = Employee(
        business_id=business_id,
        user_id=user_id,
        employee_number=employee_number,
        full_name=full_name,
        phone=phone,
        email=email,
        job_title=job_title,
        department=department,
        branch=branch,
        skills=skills,
        qualifications=qualifications,
        status=status_value,
        hire_date=hire_date,
        hourly_rate=hourly_rate,
        commission_rate=commission_rate,
        notes=notes,
    )

    db.add(employee)
    db.flush()

    create_audit_log(
        db=db,
        business_id=business_id,
        user_id=actor_user_id,
        action="EMPLOYEE_CREATED",
        entity_type="EMPLOYEE",
        entity_id=employee.id,
        details=f"Employee {employee.employee_number} created",
    )

    db.commit()
    db.refresh(employee)

    return employee


def list_employees(
    db: Session,
    business_id: str,
    status_filter: Optional[str] = None,
):
    query = db.query(Employee).filter(
        Employee.business_id == business_id
    )

    if status_filter:
        if status_filter not in EMPLOYEE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid employee status",
            )
        query = query.filter(Employee.status == status_filter)

    return query.order_by(Employee.created_at.desc()).all()


def get_employee(
    db: Session,
    business_id: str,
    employee_id: str,
):
    return _get_employee(db, business_id, employee_id)


def update_employee(
    db: Session,
    business_id: str,
    actor_user_id: str,
    employee_id: str,
    **changes,
):
    employee = _get_employee(
        db,
        business_id,
        employee_id,
    )

    if "employee_number" in changes and changes["employee_number"] is not None:
        _validate_employee_number(
            db,
            business_id,
            changes["employee_number"],
            exclude_employee_id=employee.id,
        )

    if "user_id" in changes:
        new_user_id = changes["user_id"]

        if new_user_id != employee.user_id:
            _validate_user_link(
                db,
                business_id,
                new_user_id,
            )

    if "status_value" in changes:
        new_status = changes.pop("status_value")

        if new_status not in EMPLOYEE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid employee status",
            )

        changes["status"] = new_status

    for field, value in changes.items():
        if value is not None and hasattr(employee, field):
            setattr(employee, field, value)

    db.flush()

    create_audit_log(
        db=db,
        business_id=business_id,
        user_id=actor_user_id,
        action="EMPLOYEE_UPDATED",
        entity_type="EMPLOYEE",
        entity_id=employee.id,
        details=f"Employee {employee.employee_number} updated",
    )

    db.commit()
    db.refresh(employee)

    return employee


def change_employee_status(
    db: Session,
    business_id: str,
    actor_user_id: str,
    employee_id: str,
    new_status: str,
):
    if new_status not in EMPLOYEE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid employee status",
        )

    employee = _get_employee(
        db,
        business_id,
        employee_id,
    )

    old_status = employee.status
    employee.status = new_status

    db.flush()

    create_audit_log(
        db=db,
        business_id=business_id,
        user_id=actor_user_id,
        action="EMPLOYEE_STATUS_CHANGED",
        entity_type="EMPLOYEE",
        entity_id=employee.id,
        details=f"Employee status changed from {old_status} to {new_status}",
    )

    db.commit()
    db.refresh(employee)

    return employee
