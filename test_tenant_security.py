import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from fastapi.testclient import TestClient
from datetime import datetime

from main import app


client = TestClient(app)

print("=" * 50)
print(" IMRAN BUSINESS OS")
print(" MULTI-TENANT SECURITY TEST")
print("=" * 50)


def register(email, business):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": business + " Owner",
            "email": email,
            "password": "StrongPassword123!",
            "business_name": business,
            "business_category": "retail",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en"
        }
    )

    assert response.status_code == 200, response.text

    data = response.json()

    return data["access_token"], data["business"]["id"]


RUN_ID = datetime.now().strftime("%Y%m%d%H%M%S%f")

print("\n[1] Creating Business A...")
token_a, business_a = register(
    "owner_a_security_test_" + RUN_ID + "@example.com",
    "Security Test Business A"
)
print("PASS: Business A created")


print("\n[2] Creating Business B...")
token_b, business_b = register(
    "owner_b_security_test_" + RUN_ID + "@example.com",
    "Security Test Business B"
)
print("PASS: Business B created")


assert business_a != business_b
print("PASS: Businesses have different tenant IDs")


headers_a = {
    "Authorization": f"Bearer {token_a}"
}

headers_b = {
    "Authorization": f"Bearer {token_b}"
}


print("\n[3] Creating customer in Business A...")

customer_response = client.post(
    "/api/v1/customers",
    headers=headers_a,
    json={
        "name": "Business A Private Customer",
        "phone": "+265000000001"
    }
)

assert customer_response.status_code == 200, customer_response.text

customer_a = customer_response.json()

print("PASS: Customer created in Business A")


print("\n[4] Creating product in Business A...")

product_response = client.post(
    "/api/v1/products",
    headers=headers_a,
    json={
        "name": "Business A Private Product",
        "sku": "A-PRIVATE-001",
        "type": "product",
        "price": 100,
        "cost": 50,
        "quantity": 10
    }
)

assert product_response.status_code == 200, product_response.text

product_a = product_response.json()

print("PASS: Product created in Business A")


print("\n[5] Business A reading its customer...")

response = client.get(
    f"/api/v1/customers/{customer_a['id']}",
    headers=headers_a
)

assert response.status_code == 200

print("PASS: Business A can access its own customer")


print("\n[6] Business B attempting to read Business A customer...")

response = client.get(
    f"/api/v1/customers/{customer_a['id']}",
    headers=headers_b
)

assert response.status_code == 404

print("PASS: Business B cannot access Business A customer")


print("\n[7] Business B attempting to read Business A product...")

response = client.get(
    f"/api/v1/products/{product_a['id']}",
    headers=headers_b
)

assert response.status_code == 404

print("PASS: Business B cannot access Business A product")


print("\n[8] Business B attempting to delete Business A customer...")

response = client.delete(
    f"/api/v1/customers/{customer_a['id']}",
    headers=headers_b
)

assert response.status_code == 404

print("PASS: Business B cannot delete Business A customer")


print("\n[9] Unauthenticated customer request...")

response = client.get(
    "/api/v1/customers"
)

assert response.status_code in (401, 403)

print("PASS: Unauthenticated request rejected")


print("\n[10] Business A listing its customers...")

response = client.get(
    "/api/v1/customers",
    headers=headers_a
)

assert response.status_code == 200

customers = response.json()

assert any(
    c["id"] == customer_a["id"]
    for c in customers
)

print("PASS: Business A sees its own customer")


print("\n[11] Business B listing customers...")

response = client.get(
    "/api/v1/customers",
    headers=headers_b
)

assert response.status_code == 200

customers_b = response.json()

assert not any(
    c["id"] == customer_a["id"]
    for c in customers_b
)

print("PASS: Business B does not see Business A customer")


print("\n" + "=" * 50)
print(" TENANT SECURITY TEST COMPLETE")
print("=" * 50)

print("""
PASS: Business isolation
PASS: Customer isolation
PASS: Product isolation
PASS: Delete protection
PASS: Authentication enforcement
PASS: Cross-tenant access protection
""")

print("RESULT: SECURITY TEST PASSED")
print("=" * 50)
