from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import (
    Service,
    ServiceEmployee,
    ServiceMaterial,
    Employee,
    Product,
)
from app.core.auth import get_current_user, require_manager
from app.services.audit import create_audit_log

router = APIRouter(prefix="/api/v1/services", tags=["services"])


class ServiceCreate(BaseModel):
    service_code: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: float = 0
    cost: float = 0
    duration_minutes: Optional[float] = None
    required_skills: Optional[str] = None
    tax_rate: float = 0
    discount_rate: float = 0
    warranty_days: Optional[float] = None
    status: str = "ACTIVE"
    notes: Optional[str] = None


class ServiceUpdate(BaseModel):
    service_code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    duration_minutes: Optional[float] = None
    required_skills: Optional[str] = None
    tax_rate: Optional[float] = None
    discount_rate: Optional[float] = None
    warranty_days: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AssignEmployeeRequest(BaseModel):
    employee_id: str


class AddMaterialRequest(BaseModel):
    product_id: str
    quantity: float


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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    if payload.price < 0 or payload.cost < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price and cost cannot be negative",
        )

    if payload.duration_minutes is not None and payload.duration_minutes < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duration cannot be negative",
        )

    if not 0 <= payload.tax_rate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tax rate cannot be negative",
        )

    if not 0 <= payload.discount_rate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount rate cannot be negative",
        )

    duplicate = (
        db.query(Service)
        .filter(
            Service.business_id == current_user.business_id,
            Service.service_code == payload.service_code,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service code already exists",
        )

    service = Service(
        business_id=current_user.business_id,
        **payload.model_dump(),
    )

    db.add(service)
    db.flush()

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="CREATE_SERVICE",
        entity_type="SERVICE",
        entity_id=service.id,
        details=f"Created service {service.service_code}",
    )

    db.commit()
    db.refresh(service)

    return service


@router.get("")
def list_services(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    services = (
        db.query(Service)
        .filter(Service.business_id == current_user.business_id)
        .order_by(Service.created_at.desc())
        .all()
    )

    return services


@router.get("/{service_id}")
def get_service(
    service_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = _get_service(
        db,
        current_user.business_id,
        service_id,
    )

    employees = (
        db.query(ServiceEmployee, Employee)
        .join(Employee, Employee.id == ServiceEmployee.employee_id)
        .filter(
            ServiceEmployee.service_id == service.id,
            Employee.business_id == current_user.business_id,
        )
        .all()
    )

    materials = (
        db.query(ServiceMaterial, Product)
        .join(Product, Product.id == ServiceMaterial.product_id)
        .filter(
            ServiceMaterial.service_id == service.id,
            Product.business_id == current_user.business_id,
        )
        .all()
    )

    return {
        "service": service,
        "employees": [
            {
                "id": employee.id,
                "employee_number": employee.employee_number,
                "full_name": employee.full_name,
                "job_title": employee.job_title,
            }
            for _, employee in employees
        ],
        "materials": [
            {
                "id": material.id,
                "product_id": material.product_id,
                "product_name": product.name,
                "quantity": material.quantity,
            }
            for material, product in materials
        ],
    }


@router.patch("/{service_id}")
def update_service(
    service_id: str,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    service = _get_service(
        db,
        current_user.business_id,
        service_id,
    )

    values = payload.model_dump(exclude_unset=True)

    if "price" in values and values["price"] is not None and values["price"] < 0:
        raise HTTPException(400, "Price cannot be negative")

    if "cost" in values and values["cost"] is not None and values["cost"] < 0:
        raise HTTPException(400, "Cost cannot be negative")

    if "duration_minutes" in values and values["duration_minutes"] is not None:
        if values["duration_minutes"] < 0:
            raise HTTPException(400, "Duration cannot be negative")

    if "service_code" in values:
        duplicate = (
            db.query(Service)
            .filter(
                Service.business_id == current_user.business_id,
                Service.service_code == values["service_code"],
                Service.id != service.id,
            )
            .first()
        )

        if duplicate:
            raise HTTPException(409, "Service code already exists")

    for key, value in values.items():
        setattr(service, key, value)

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="UPDATE_SERVICE",
        entity_type="SERVICE",
        entity_id=service.id,
        details=f"Updated service {service.service_code}",
    )

    db.commit()
    db.refresh(service)

    return service


@router.patch("/{service_id}/status")
def update_service_status(
    service_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    service = _get_service(
        db,
        current_user.business_id,
        service_id,
    )

    new_status = payload.get("status")

    if not new_status:
        raise HTTPException(400, "status is required")

    service.status = new_status

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="UPDATE_SERVICE_STATUS",
        entity_type="SERVICE",
        entity_id=service.id,
        details=f"Service status changed to {new_status}",
    )

    db.commit()
    db.refresh(service)

    return service


@router.post("/{service_id}/employees")
def assign_employee(
    service_id: str,
    payload: AssignEmployeeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    service = _get_service(
        db,
        current_user.business_id,
        service_id,
    )

    employee = (
        db.query(Employee)
        .filter(
            Employee.id == payload.employee_id,
            Employee.business_id == current_user.business_id,
        )
        .first()
    )

    if not employee:
        raise HTTPException(404, "Employee not found")

    existing = (
        db.query(ServiceEmployee)
        .filter(
            ServiceEmployee.service_id == service.id,
            ServiceEmployee.employee_id == employee.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(409, "Employee already assigned to service")

    assignment = ServiceEmployee(
        service_id=service.id,
        employee_id=employee.id,
    )

    db.add(assignment)

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="ASSIGN_SERVICE_EMPLOYEE",
        entity_type="SERVICE",
        entity_id=service.id,
        details=f"Assigned employee {employee.employee_number}",
    )

    db.commit()
    db.refresh(assignment)

    return assignment


@router.delete("/{service_id}/employees/{employee_id}")
def remove_employee(
    service_id: str,
    employee_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    service = _get_service(
        db,
        current_user.business_id,
        service_id,
    )

    assignment = (
        db.query(ServiceEmployee)
        .join(Employee, Employee.id == ServiceEmployee.employee_id)
        .filter(
            ServiceEmployee.service_id == service.id,
            ServiceEmployee.employee_id == employee_id,
            Employee.business_id == current_user.business_id,
        )
        .first()
    )

    if not assignment:
        raise HTTPException(404, "Service employee assignment not found")

    db.delete(assignment)

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="REMOVE_SERVICE_EMPLOYEE",
        entity_type="SERVICE",
        entity_id=service.id,
        details=f"Removed employee {employee_id}",
    )

    db.commit()

    return {"status": "removed"}


@router.post("/{service_id}/materials")
def add_material(
    service_id: str,
    payload: AddMaterialRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    if payload.quantity <= 0:
        raise HTTPException(400, "Material quantity must be greater than zero")

    service = _get_service(
        db,
        current_user.business_id,
        service_id,
    )

    product = (
        db.query(Product)
        .filter(
            Product.id == payload.product_id,
            Product.business_id == current_user.business_id,
        )
        .first()
    )

    if not product:
        raise HTTPException(404, "Product not found")

    existing = (
        db.query(ServiceMaterial)
        .filter(
            ServiceMaterial.service_id == service.id,
            ServiceMaterial.product_id == product.id,
        )
        .first()
    )

    if existing:
        existing.quantity = payload.quantity
        material = existing
    else:
        material = ServiceMaterial(
            service_id=service.id,
            product_id=product.id,
            quantity=payload.quantity,
        )
        db.add(material)

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="ADD_SERVICE_MATERIAL",
        entity_type="SERVICE",
        entity_id=service.id,
        details=f"Configured material {product.name}: {payload.quantity}",
    )

    db.commit()
    db.refresh(material)

    return material


@router.delete("/{service_id}/materials/{product_id}")
def remove_material(
    service_id: str,
    product_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    service = _get_service(
        db,
        current_user.business_id,
        service_id,
    )

    material = (
        db.query(ServiceMaterial)
        .join(Product, Product.id == ServiceMaterial.product_id)
        .filter(
            ServiceMaterial.service_id == service.id,
            ServiceMaterial.product_id == product_id,
            Product.business_id == current_user.business_id,
        )
        .first()
    )

    if not material:
        raise HTTPException(404, "Service material not found")

    db.delete(material)

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="REMOVE_SERVICE_MATERIAL",
        entity_type="SERVICE",
        entity_id=service.id,
        details=f"Removed material {product_id}",
    )

    db.commit()

    return {"status": "removed"}
