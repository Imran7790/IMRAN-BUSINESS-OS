from fastapi.testclient import TestClient
from main import app
import uuid

client = TestClient(app)


def unique_email(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@test.local"


def register_business():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Auth Security Owner",
            "email": unique_email("auth"),
            "password": "TestPassword123!",
            "business_name": "Authentication Security Business",
            "business_category": "retail",
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

    return token


def test_authentication_security():
    # =========================================================
    # 1. Protected endpoint without authentication
    # =========================================================
    response = client.get("/api/v1/businesses/me")

    assert response.status_code in (401, 403), response.text

    print("UNAUTHENTICATED ACCESS BLOCKED: PASS")

    # =========================================================
    # 2. Invalid bearer token
    # =========================================================
    response = client.get(
        "/api/v1/businesses/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code in (401, 403), response.text

    print("INVALID TOKEN BLOCKED: PASS")

    # =========================================================
    # 3. Empty bearer token
    # =========================================================
    response = client.get(
        "/api/v1/businesses/me",
        headers={
            "Authorization": "Bearer "
        },
    )

    assert response.status_code in (401, 403), response.text

    print("EMPTY TOKEN BLOCKED: PASS")

    # =========================================================
    # 4. Valid token works
    # =========================================================
    token = register_business()

    auth = {
        "Authorization": f"Bearer {token}"
    }

    response = client.get(
        "/api/v1/businesses/me",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    print("VALID TOKEN ACCEPTED: PASS")

    # =========================================================
    # 5. Protected customer endpoint without token
    # =========================================================
    response = client.get("/api/v1/customers")

    assert response.status_code in (401, 403), response.text

    print("CUSTOMERS UNAUTHENTICATED BLOCKED: PASS")

    # =========================================================
    # 6. Protected product endpoint without token
    # =========================================================
    response = client.get("/api/v1/products")

    assert response.status_code in (401, 403), response.text

    print("PRODUCTS UNAUTHENTICATED BLOCKED: PASS")

    # =========================================================
    # 7. Protected invoice endpoint without token
    # =========================================================
    response = client.get("/api/v1/invoices")

    assert response.status_code in (401, 403), response.text

    print("INVOICES UNAUTHENTICATED BLOCKED: PASS")

    # =========================================================
    # 8. Protected payment endpoint without token
    # =========================================================
    fake_invoice_id = str(uuid.uuid4())

    response = client.get(
        f"/api/v1/invoices/{fake_invoice_id}/payments"
    )

    assert response.status_code in (401, 403), response.text

    print("PAYMENTS UNAUTHENTICATED BLOCKED: PASS")

    # =========================================================
    # Final result
    # =========================================================
    print()
    print("============================================================")
    print(" AUTHENTICATION SECURITY TEST: PASS")
    print("============================================================")


if __name__ == "__main__":
    test_authentication_security()
