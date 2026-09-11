
from datetime import datetime
import uuid

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def unique_email(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@test.local"


def register_business(name, prefix):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": f"{name} Owner",
            "email": unique_email(prefix),
            "password": "TestPassword123!",
            "business_name": name,
            "business_category": "professional_services",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en",
        },
    )
    assert response.status_code in (200, 201), response.text
    data = response.json()
    token = data.get("access_token") or data.get("token")
    assert token, data
    return token, data


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_customer(token, name):
    response = client.post(
        "/api/v1/customers",
        headers=auth(token),
        json={
            "name": name,
            "phone": "+265888000000",
            "email": unique_email("customer"),
            "address": "Lilongwe",
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


def get_user_id_from_token(token):
    from app.database import SessionLocal
    from app.models.core import User
    import jwt

    parts = token.split(".")
    assert len(parts) == 3, "Invalid JWT format"
    import json
    import base64
    payload_part = parts[1] + "=" * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_part).decode())

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == payload["sub"]).first()
        assert user is not None, "Token user not found"
        return user.id
    finally:
        db.close()


def test_appointment_integration():
    print("============================================================")
    print(" APPOINTMENT INTEGRATION TEST")
    print("============================================================")

    # 1. Business A
    token_a, data_a = register_business(
        "Appointment Business A",
        "appt-a",
    )
    auth_a = auth(token_a)
    print("[1] BUSINESS A: PASS")

    # 2. Business B
    token_b, data_b = register_business(
        "Appointment Business B",
        "appt-b",
    )
    auth_b = auth(token_b)
    print("[2] BUSINESS B: PASS")

    # 3. Customer A
    customer_a = create_customer(
        token_a,
        "Appointment Customer A",
    )
    print("[3] CUSTOMER A: PASS")

    # 4. Create appointment
    assigned_user_a = get_user_id_from_token(token_a)

    start = datetime(2030, 1, 15, 9, 0, 0)
    end = datetime(2030, 1, 15, 10, 0, 0)

    response = client.post(
        "/api/v1/appointments",
        headers=auth_a,
        json={
            "customer_id": customer_a,
            "assigned_user_id": assigned_user_a,
            "title": "Initial consultation",
            "appointment_type": "CONSULTATION",
            "description": "Initial client consultation",
            "location": "Lilongwe Office",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "status": "SCHEDULED",
            "notes": "Bring required documents",
        },
    )

    assert response.status_code == 201, response.text
    appointment_id = response.json()["id"]
    assert response.json()["status"] == "SCHEDULED"
    print("[4] CREATE APPOINTMENT: PASS")

    # 5. Get appointment
    response = client.get(
        f"/api/v1/appointments/{appointment_id}",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == appointment_id
    print("[5] GET APPOINTMENT: PASS")

    # 6. List appointments
    response = client.get(
        "/api/v1/appointments",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    assert any(
        item["id"] == appointment_id
        for item in response.json()
    )
    print("[6] LIST APPOINTMENTS: PASS")

    # 7. Overlapping appointment for same user must fail
    response = client.post(
        "/api/v1/appointments",
        headers=auth_a,
        json={
            "customer_id": customer_a,
            "assigned_user_id": assigned_user_a,
            "title": "Overlapping appointment",
            "appointment_type": "CONSULTATION",
            "start_at": "2030-01-15T09:30:00",
            "end_at": "2030-01-15T10:30:00",
        },
    )

    assert response.status_code == 409, response.text
    print("[7] OVERLAPPING APPOINTMENT BLOCKED: PASS")

    # 8. Unassigned appointment can overlap
    response = client.post(
        "/api/v1/appointments",
        headers=auth_a,
        json={
            "customer_id": customer_a,
            "title": "Unassigned appointment",
            "appointment_type": "GENERAL",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
        },
    )

    assert response.status_code == 201, response.text
    print("[8] UNASSIGNED OVERLAP ALLOWED: PASS")

    # 9. Invalid time window
    response = client.post(
        "/api/v1/appointments",
        headers=auth_a,
        json={
            "customer_id": customer_a,
            "assigned_user_id": assigned_user_a,
            "title": "Invalid appointment",
            "start_at": "2030-01-15T11:00:00",
            "end_at": "2030-01-15T10:00:00",
        },
    )

    assert response.status_code == 400, response.text
    print("[9] INVALID TIME WINDOW BLOCKED: PASS")

    # 10. Cross-tenant customer
    response = client.post(
        "/api/v1/appointments",
        headers=auth_b,
        json={
            "customer_id": customer_a,
            "title": "Cross tenant customer",
            "start_at": "2030-01-16T09:00:00",
            "end_at": "2030-01-16T10:00:00",
        },
    )

    assert response.status_code == 404, response.text
    print("[10] CROSS-TENANT CUSTOMER BLOCKED: PASS")

    # 11. Update / reschedule
    new_start = datetime(2030, 1, 15, 13, 0, 0)
    new_end = datetime(2030, 1, 15, 14, 0, 0)

    response = client.patch(
        f"/api/v1/appointments/{appointment_id}",
        headers=auth_a,
        json={
            "customer_id": customer_a,
            "assigned_user_id": assigned_user_a,
            "title": "Rescheduled consultation",
            "appointment_type": "CONSULTATION",
            "description": "Updated consultation",
            "location": "Lilongwe Office",
            "start_at": new_start.isoformat(),
            "end_at": new_end.isoformat(),
            "notes": "Rescheduled",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Rescheduled consultation"
    print("[11] UPDATE/RESCHEDULE: PASS")

    # 12. Confirm
    response = client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=auth_a,
        json={"status": "CONFIRMED"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CONFIRMED"
    print("[12] CONFIRM APPOINTMENT: PASS")

    # 13. Complete
    response = client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=auth_a,
        json={"status": "COMPLETED"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "COMPLETED"
    print("[13] COMPLETE APPOINTMENT: PASS")

    # 14. Cross-tenant direct access
    response = client.get(
        f"/api/v1/appointments/{appointment_id}",
        headers=auth_b,
    )

    assert response.status_code == 404, response.text
    print("[14] CROSS-TENANT APPOINTMENT ACCESS BLOCKED: PASS")

    # 15. Status filter
    response = client.get(
        "/api/v1/appointments?status_filter=COMPLETED",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    assert any(
        item["id"] == appointment_id
        for item in response.json()
    )
    print("[15] STATUS FILTER: PASS")

    # 16. Business B list isolation
    response = client.get(
        "/api/v1/appointments",
        headers=auth_b,
    )

    assert response.status_code == 200, response.text
    assert all(
        item["business_id"] != data_a.get("business_id")
        for item in response.json()
    )
    print("[16] LIST TENANT ISOLATION: PASS")

    print("============================================================")
    print(" APPOINTMENT INTEGRATION TEST: PASS")
    print("============================================================")


if __name__ == "__main__":
    test_appointment_integration()
