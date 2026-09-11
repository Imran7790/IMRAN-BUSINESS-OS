from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_manager
from app.database import get_db
from app.models.core import Employee, User
from app.services.employees import (
    create_employee,
    list_employees,
    get_employee,
    update_employee,
    change_employee_status,
)

router = APIRouter(
    prefix="/api/v1/employees",
    tags=["Employees"],
)


class EmployeeCreate(BaseModel):
    employee_number: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    job_title: str = Field(min_length=1)

    user_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    skills: Optional[str] = None
    qualifications: Optional[str] = None
    status: str = "ACTIVE"
    hire_date: Optional[date] = None
    hourly_rate: Optional[float] = Field(default=None, ge=0)
    commission_rate: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


class EmployeeUpdate(BaseModel):
    employee_number: Optional[str] = Field(default=None, min_length=1)
    full_name: Optional[str] = Field(default=None, min_length=1)
    job_title: Optional[str] = Field(default=None, min_length=1)

    user_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    skills: Optional[str] = None
    qualifications: Optional[str] = None
    status: Optional[str] = None
    hire_date: Optional[date] = None
    hourly_rate: Optional[float] = Field(default=None, ge=0)
    commission_rate: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


class EmployeeStatusUpdate(BaseModel):
    status: str


def _employee_response(employee: Employee):
    return {
        "id": employee.id,
        "business_id": employee.business_id,
        "user_id": employee.user_id,
        "employee_number": employee.employee_number,
        "full_name": employee.full_name,
        "phone": employee.phone,
        "email": employee.email,
        "job_title": employee.job_title,
        "department": employee.department,
        "branch": employee.branch,
        "skills": employee.skills,
        "qualifications": employee.qualifications,
        "status": employee.status,
        "hire_date": employee.hire_date,
        "hourly_rate": employee.hourly_rate,
        "commission_rate": employee.commission_rate,
        "notes": employee.notes,
        "created_at": employee.created_at,
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_employee_endpoint(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    employee = create_employee(
        db=db,
        business_id=current_user.business_id,
        actor_user_id=current_user.id,
        employee_number=payload.employee_number,
        full_name=payload.full_name,
        job_title=payload.job_title,
        phone=payload.phone,
        email=payload.email,
        department=payload.department,
        branch=payload.branch,
        skills=payload.skills,
        qualifications=payload.qualifications,
        status_value=payload.status,
        hire_date=payload.hire_date,
        hourly_rate=payload.hourly_rate,
        commission_rate=payload.commission_rate,
        notes=payload.notes,
        user_id=payload.user_id,
    )

    return _employee_response(employee)


@router.get("")
def list_employees_endpoint(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employees = list_employees(
        db=db,
        business_id=current_user.business_id,
        status_filter=status_filter,
    )

    return [_employee_response(employee) for employee in employees]


@router.get("/{employee_id}")
def get_employee_endpoint(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = get_employee(
        db=db,
        business_id=current_user.business_id,
        employee_id=employee_id,
    )

    return _employee_response(employee)


@router.patch("/{employee_id}")
def update_employee_endpoint(
    employee_id: str,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    changes = payload.model_dump(exclude_unset=True)

    employee = update_employee(
        db=db,
        business_id=current_user.business_id,
        actor_user_id=current_user.id,
        employee_id=employee_id,
        **changes,
    )

    return _employee_response(employee)


@router.patch("/{employee_id}/status")
def change_employee_status_endpoint(
    employee_id: str,
    payload: EmployeeStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    employee = change_employee_status(
        db=db,
        business_id=current_user.business_id,
        actor_user_id=current_user.id,
        employee_id=employee_id,
        new_status=payload.status,
    )

    return _employee_response(employee)
