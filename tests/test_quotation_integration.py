from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def unique_email(prefix):
    return f"{prefix}_{uuid4().hex[:8]}@example.com"


def register_business(prefix):
    email = unique_email(prefix)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": f"{prefix} Owner",
            "email": email,
            "password": "StrongPassword123!",
            "business_name": f"{prefix} Business",
            "business_category": "retail",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    return data["access_token"], data


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_quotation_complete_workflow():
    token_a, business_a = register_business("QuotationA")
    token_b, business_b = register_business("QuotationB")

    headers_a = auth(token_a)
    headers_b = auth(token_b)

    # Customer
    customer_response = client.post(
        "/api/v1/customers",
        headers=headers_a,
        json={
            "name": "Quotation Customer",
            "phone": "+265880000001",
            "email": "customer@example.com",
            "address": "Lilongwe",
        },
    )

    assert customer_response.status_code == 200, customer_response.text
    customer_id = customer_response.json()["id"]

    # Product
    product_response = client.post(
        "/api/v1/products",
        headers=headers_a,
        json={
            "name": "Business Laptop",
            "sku": f"LAPTOP-{uuid4().hex[:8]}",
            "type": "product",
            "price": 500000,
            "cost": 350000,
        },
    )

    assert product_response.status_code == 200, product_response.text
    product_id = product_response.json()["id"]

    # Create quotation
    quotation_response = client.post(
        "/api/v1/quotations",
        headers=headers_a,
        json={
            "customer_id": customer_id,
            "valid_until": (date.today() + timedelta(days=30)).isoformat(),
            "discount": 50000,
            "tax": 72000,
            "notes": "Quotation integration test",
            "items": [
                {
                    "product_id": product_id,
                    "description": "Business Laptop",
                    "quantity": 2,
                    "unit_price": 500000,
                }
            ],
        },
    )

    assert quotation_response.status_code == 201, quotation_response.text

    quotation = quotation_response.json()
    quotation_id = quotation["id"]

    assert quotation["business_id"] == business_a["business"]["id"]
    assert quotation["currency_code"] == "MWK"
    assert quotation["subtotal"] == 1000000
    assert quotation["discount"] == 50000
    assert quotation["tax"] == 72000
    assert quotation["total"] == 1022000
    assert quotation["status"] == "DRAFT"
    assert len(quotation["items"]) == 1
    assert quotation["items"][0]["line_total"] == 1000000

    # Get quotation
    response = client.get(
        f"/api/v1/quotations/{quotation_id}",
        headers=headers_a,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == quotation_id

    # Business B must not access Business A quotation
    response = client.get(
        f"/api/v1/quotations/{quotation_id}",
        headers=headers_b,
    )

    assert response.status_code == 404

    # Send
    response = client.post(
        f"/api/v1/quotations/{quotation_id}/send",
        headers=headers_a,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "SENT"

    # Accept
    response = client.post(
        f"/api/v1/quotations/{quotation_id}/accept",
        headers=headers_a,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACCEPTED"

    # Cannot reject an accepted quotation
    response = client.post(
        f"/api/v1/quotations/{quotation_id}/reject",
        headers=headers_a,
    )

    assert response.status_code == 400

    # Business B cannot modify Business A quotation
    response = client.post(
        f"/api/v1/quotations/{quotation_id}/cancel",
        headers=headers_b,
    )

    assert response.status_code == 404

    # Final state
    response = client.get(
        f"/api/v1/quotations/{quotation_id}",
        headers=headers_a,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"

    print("QUOTATION COMPLETE WORKFLOW: PASS")
    print("QUOTATION TENANT ISOLATION: PASS")
    print("QUOTATION CALCULATIONS: PASS")
    print("QUOTATION STATUS TRANSITIONS: PASS")
