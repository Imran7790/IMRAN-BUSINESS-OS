from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.database import Base, get_db
from app.models.core import (
    Business,
    User,
    Customer,
    Employee,
    Service,
    ServiceJob,
    AuditLog,
)
from app.core.auth import hash_password, create_token


@pytest.fixture()
def test_environment():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, TestingSessionLocal

    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def make_business(db):
    business = Business(
        name="Service Job Test Business",
        category="ELECTRICAL",
        country_code="MW",
        currency_code="MWK",
        timezone="Africa/Blantyre",
        language_code="en",
    )
    db.add(business)
    db.flush()

    user = User(
        business_id=business.id,
        email=f"servicejob-{business.id}@example.com",
        password_hash=hash_password("TestPassword123!"),
        role="owner",
    )
    db.add(user)
    db.flush()

    customer = Customer(
        business_id=business.id,
        name="Service Job Customer",
        phone="0999000000",
    )
    db.add(customer)
    db.flush()

    employee = Employee(
        business_id=business.id,
        employee_number=f"E-{business.id[:8]}",
        full_name="Service Technician",
        job_title="Technician",
        status="ACTIVE",
    )
    db.add(employee)
    db.flush()

    service = Service(
        business_id=business.id,
        service_code=f"S-{business.id[:8]}",
        name="Electrical Installation",
        description="Electrical installation service",
        category="ELECTRICAL",
        price=100000,
        cost=50000,
        duration_minutes=120,
        status="ACTIVE",
    )
    db.add(service)

    db.commit()

    return {
        "business_id": business.id,
        "user_id": user.id,
        "customer_id": customer.id,
        "employee_id": employee.id,
        "service_id": service.id,
    }


def auth_headers(user_id, business_id):
    token = create_token(user_id, business_id)
    return {"Authorization": f"Bearer {token}"}


def test_service_job_full_lifecycle(test_environment):
    client, SessionLocal = test_environment

    db = SessionLocal()
    data = make_business(db)

    headers = auth_headers(
        data["user_id"],
        data["business_id"],
    )

    start = datetime.now(timezone.utc).replace(tzinfo=None)
    end = start + timedelta(hours=2)

    response = client.post(
        "/api/v1/service-jobs",
        headers=headers,
        json={
            "customer_id": data["customer_id"],
            "service_id": data["service_id"],
            "title": "Install electrical system",
            "description": "Complete domestic electrical installation",
            "priority": "HIGH",
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
            "quoted_amount": 100000,
        },
    )

    assert response.status_code == 201, response.text

    job = response.json()

    assert job["business_id"] == data["business_id"]
    assert job["customer_id"] == data["customer_id"]
    assert job["service_id"] == data["service_id"]
    assert job["status"] == "OPEN"
    assert job["priority"] == "HIGH"
    assert job["job_number"].startswith("JOB-")

    job_id = job["id"]

    response = client.post(
        f"/api/v1/service-jobs/{job_id}/assign-employee",
        headers=headers,
        params={"employee_id": data["employee_id"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["employee_id"] == data["employee_id"]

    response = client.post(
        f"/api/v1/service-jobs/{job_id}/start",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "IN_PROGRESS"
    assert response.json()["started_at"] is not None

    response = client.post(
        f"/api/v1/service-jobs/{job_id}/complete",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    completed = response.json()

    assert completed["status"] == "COMPLETED"
    assert completed["started_at"] is not None
    assert completed["completed_at"] is not None

    response = client.patch(
        f"/api/v1/service-jobs/{job_id}",
        headers=headers,
        json={"notes": "Should not be editable after completion"},
    )

    assert response.status_code == 400

    response = client.post(
        f"/api/v1/service-jobs/{job_id}/cancel",
        headers=headers,
    )

    assert response.status_code == 400

    stored_job = (
        db.query(ServiceJob)
        .filter(ServiceJob.id == job_id)
        .first()
    )

    assert stored_job is not None
    assert stored_job.status == "COMPLETED"
    assert stored_job.employee_id == data["employee_id"]

    audit_count = (
        db.query(AuditLog)
        .filter(
            AuditLog.business_id == data["business_id"],
            AuditLog.entity_type == "SERVICE_JOB",
            AuditLog.entity_id == job_id,
        )
        .count()
    )

    assert audit_count >= 4

    db.close()


def test_service_job_requires_authentication(test_environment):
    client, _ = test_environment

    response = client.get("/api/v1/service-jobs")

    assert response.status_code == 401
