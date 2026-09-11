from fastapi.testclient import TestClient
from main import app
import uuid

client = TestClient(app)


def unique_email(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@test.local"


def register_business(name, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Security Test Owner",
            "email": email,
            "password": "TestPassword123!",
            "business_name": name,
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

    business_id = data.get("business_id")

    if not business_id and isinstance(data.get("business"), dict):
        business_id = data["business"].get("id")

    assert business_id, data

    return token, business_id


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_tenant_isolation():
    # =========================================================
    # 1. Create Business A
    # =========================================================
    token_a, business_a = register_business(
        "Tenant Isolation Business A",
        unique_email("tenant-a"),
    )

    auth_a = headers(token_a)

    # =========================================================
    # 2. Create Business B
    # =========================================================
    token_b, business_b = register_business(
        "Tenant Isolation Business B",
        unique_email("tenant-b"),
    )

    auth_b = headers(token_b)

    assert business_a != business_b

    print("BUSINESS A CREATED:", business_a)
    print("BUSINESS B CREATED:", business_b)

    # =========================================================
    # 3. Business A creates customer
    # =========================================================
    response = client.post(
        "/api/v1/customers",
        headers=auth_a,
        json={
            "name": "Business A Customer",
            "phone": "+265999100001",
            "email": "customer-a@test.local",
            "address": "Lilongwe",
        },
    )

    assert response.status_code in (200, 201), response.text

    customer_a = response.json()
    customer_a_id = customer_a["id"]

    assert customer_a["business_id"] == business_a

    # =========================================================
    # 4. Business B cannot access Business A customer
    # =========================================================
    response = client.get(
        f"/api/v1/customers/{customer_a_id}",
        headers=auth_b,
    )

    assert response.status_code in (403, 404), response.text

    print("CUSTOMER TENANT ISOLATION: PASS")

    # =========================================================
    # 5. Business A creates product
    # =========================================================
    response = client.post(
        "/api/v1/products",
        headers=auth_a,
        json={
            "name": "Business A Product",
            "sku": f"SEC-{uuid.uuid4().hex[:8]}",
            "type": "product",
            "price": 10000,
            "cost": 6000,
            "quantity": 20,
        },
    )

    assert response.status_code in (200, 201), response.text

    product_a = response.json()
    product_a_id = product_a["id"]

    assert product_a["business_id"] == business_a

    # =========================================================
    # 6. Business B cannot access Business A product
    # =========================================================
    response = client.get(
        f"/api/v1/products/{product_a_id}",
        headers=auth_b,
    )

    assert response.status_code in (403, 404), response.text

    print("PRODUCT TENANT ISOLATION: PASS")

    # =========================================================
    # 7. Business B cannot delete Business A customer
    # =========================================================
    response = client.delete(
        f"/api/v1/customers/{customer_a_id}",
        headers=auth_b,
    )

    assert response.status_code in (403, 404), response.text

    print("CUSTOMER CROSS-TENANT DELETE BLOCKED: PASS")

    # =========================================================
    # 8. Business B cannot delete Business A product
    # =========================================================
    response = client.delete(
        f"/api/v1/products/{product_a_id}",
        headers=auth_b,
    )

    assert response.status_code in (403, 404), response.text

    print("PRODUCT CROSS-TENANT DELETE BLOCKED: PASS")

    # =========================================================
    # 9. Business A data remains intact
    # =========================================================
    response = client.get(
        f"/api/v1/customers/{customer_a_id}",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text

    customer_check = response.json()

    assert customer_check["business_id"] == business_a
    assert customer_check["name"] == "Business A Customer"

    response = client.get(
        f"/api/v1/products/{product_a_id}",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text

    product_check = response.json()

    assert product_check["business_id"] == business_a
    assert product_check["price"] == 10000

    print("BUSINESS A DATA INTEGRITY AFTER ATTACK: PASS")

    # =========================================================
    # 10. Business B can access its own tenant
    # =========================================================
    response = client.get(
        "/api/v1/businesses/me",
        headers=auth_b,
    )

    assert response.status_code == 200, response.text

    business_check = response.json()

    assert business_check["id"] == business_b

    print("BUSINESS B SELF ACCESS: PASS")

    print()
    print("============================================================")
    print(" TENANT ISOLATION SECURITY TEST: PASS")
    print("============================================================")


if __name__ == "__main__":
    test_tenant_isolation()
