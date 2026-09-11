import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.core import Business, User, Employee, Product
from app.core.auth import hash_password
import main


client = TestClient(main.app)


def make_business(db, name):
    business = Business(
        id=str(uuid.uuid4()),
        name=name,
        category="TEST",
        country_code="MW",
        currency_code="MWK",
        timezone="Africa/Blantyre",
        language_code="en",
    )
    db.add(business)
    db.flush()

    user = User(
        id=str(uuid.uuid4()),
        business_id=business.id,
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("TestPassword123!"),
        role="owner",
    )
    db.add(user)

    db.flush()
    return business, user


def login(email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_service_lifecycle():
    db = SessionLocal()

    try:
        business, user = make_business(db, "Service Test Business")

        employee = Employee(
            id=str(uuid.uuid4()),
            business_id=business.id,
            employee_number="EMP-SVC-001",
            full_name="Service Technician",
            job_title="Technician",
            status="ACTIVE",
        )

        product = Product(
            id=str(uuid.uuid4()),
            business_id=business.id,
            name="Test Cable",
            sku="SVC-CABLE-001",
            type="PRODUCT",
            price=5000,
            cost=3000,
            quantity=20,
            reorder_level=5,
            target_quantity=20,
        )

        db.add(employee)
        db.add(product)
        db.commit()

        headers = login(user.email)

        # CREATE
        r = client.post(
            "/api/v1/services",
            json={
                "service_code": "INSTALL-001",
                "name": "Electrical Installation",
                "description": "Electrical installation service",
                "category": "Electrical",
                "price": 100000,
                "cost": 60000,
                "duration_minutes": 120,
                "required_skills": "Electrical Installation",
                "tax_rate": 16.5,
                "discount_rate": 0,
                "warranty_days": 30,
                "status": "ACTIVE",
            },
            headers=headers,
        )

        assert r.status_code == 201, r.text
        service_id = r.json()["id"]

        # LIST
        r = client.get("/api/v1/services", headers=headers)
        assert r.status_code == 200
        assert any(x["id"] == service_id for x in r.json())

        # GET
        r = client.get(
            f"/api/v1/services/{service_id}",
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["service"]["id"] == service_id

        # UPDATE
        r = client.patch(
            f"/api/v1/services/{service_id}",
            json={
                "price": 125000,
                "duration_minutes": 150,
            },
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["price"] == 125000

        # ASSIGN EMPLOYEE
        r = client.post(
            f"/api/v1/services/{service_id}/employees",
            json={"employee_id": employee.id},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        # ADD MATERIAL
        r = client.post(
            f"/api/v1/services/{service_id}/materials",
            json={
                "product_id": product.id,
                "quantity": 2,
            },
            headers=headers,
        )
        assert r.status_code == 200, r.text

        # VERIFY RELATIONSHIPS
        r = client.get(
            f"/api/v1/services/{service_id}",
            headers=headers,
        )
        assert r.status_code == 200

        data = r.json()

        assert len(data["employees"]) == 1
        assert data["employees"][0]["id"] == employee.id

        assert len(data["materials"]) == 1
        assert data["materials"][0]["product_id"] == product.id
        assert data["materials"][0]["quantity"] == 2

        # STATUS
        r = client.patch(
            f"/api/v1/services/{service_id}/status",
            json={"status": "INACTIVE"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "INACTIVE"

        # REMOVE EMPLOYEE
        r = client.delete(
            f"/api/v1/services/{service_id}/employees/{employee.id}",
            headers=headers,
        )
        assert r.status_code == 200

        # REMOVE MATERIAL
        r = client.delete(
            f"/api/v1/services/{service_id}/materials/{product.id}",
            headers=headers,
        )
        assert r.status_code == 200

        # VERIFY EMPTY RELATIONSHIPS
        r = client.get(
            f"/api/v1/services/{service_id}",
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["employees"] == []
        assert data["materials"] == []

        print("SERVICE LIFECYCLE: PASS")

    finally:
        db.close()


def test_service_requires_authentication():
    r = client.get("/api/v1/services")
    assert r.status_code == 401
    print("SERVICE AUTHENTICATION: PASS")
