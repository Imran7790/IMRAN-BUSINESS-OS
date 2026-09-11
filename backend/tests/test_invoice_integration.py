from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def unique_email(prefix):
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:10]}@test.local"


def register_business(name, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Invoice Test Owner",
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


def test_invoice_complete_workflow():
    token, business_id = register_business(
        "Invoice Integration Business",
        unique_email("invoice"),
    )

    auth = headers(token)

    # ---------------------------------------------------------
    # 1. Create customer
    # ---------------------------------------------------------
    response = client.post(
        "/api/v1/customers",
        headers=auth,
        json={
            "name": "Invoice Test Customer",
            "phone": "+265999000001",
            "email": "customer@test.local",
            "address": "Lilongwe",
        },
    )

    assert response.status_code in (200, 201), response.text

    customer = response.json()
    customer_id = customer["id"]

    # ---------------------------------------------------------
    # 2. Create product
    # ---------------------------------------------------------
    response = client.post(
        "/api/v1/products",
        headers=auth,
        json={
            "name": "Invoice Test Product",
            "sku": "INV-TEST-001",
            "type": "product",
            "price": 10000,
            "cost": 6000,
            "quantity": 20,
        },
    )

    assert response.status_code in (200, 201), response.text

    product = response.json()
    product_id = product["id"]

    # ---------------------------------------------------------
    # 3. Create invoice
    # ---------------------------------------------------------
    response = client.post(
        "/api/v1/invoices",
        headers=auth,
        json={
            "customer_id": customer_id,
            "currency_code": "MWK",
            "discount": 5000,
            "tax": 0,
            "items": [
                {
                    "product_id": product_id,
                    "description": "Invoice Test Product",
                    "quantity": 2,
                    "unit_price": 10000,
                }
            ],
        },
    )

    assert response.status_code in (200, 201), response.text

    invoice = response.json()

    assert invoice["business_id"] == business_id
    assert invoice["currency_code"] == "MWK"

    assert invoice["subtotal"] == 20000
    assert invoice["discount"] == 5000
    assert invoice["tax"] == 0
    assert invoice["total"] == 15000
    assert invoice["status"] == "DRAFT"

    invoice_id = invoice["id"]

    print("CREATE INVOICE: PASS")
    print("SUBTOTAL:", invoice["subtotal"])
    print("DISCOUNT:", invoice["discount"])
    print("TOTAL:", invoice["total"])

    # ---------------------------------------------------------
    # 4. Verify GET invoice
    # ---------------------------------------------------------
    response = client.get(
        f"/api/v1/invoices/{invoice_id}",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    fetched = response.json()

    assert fetched["id"] == invoice_id
    assert fetched["total"] == 15000
    assert fetched["status"] == "DRAFT"

    print("GET INVOICE: PASS")

    # ---------------------------------------------------------
    # 5. Verify inventory was NOT changed by invoice creation
    # ---------------------------------------------------------
    response = client.get(
        f"/api/v1/products/{product_id}",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    product_after_invoice = response.json()

    assert product_after_invoice["quantity"] == 20

    print("INVOICE DOES NOT MUTATE INVENTORY: PASS")

    # ---------------------------------------------------------
    # 6. Issue invoice
    # ---------------------------------------------------------
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/issue",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    issued = response.json()

    assert issued["id"] == invoice_id
    assert issued["status"] == "ISSUED"

    print("ISSUE INVOICE: PASS")

    # ---------------------------------------------------------
    # 7. Verify issued invoice
    # ---------------------------------------------------------
    response = client.get(
        f"/api/v1/invoices/{invoice_id}",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    issued_check = response.json()

    assert issued_check["status"] == "ISSUED"
    assert issued_check["total"] == 15000

    print("ISSUED INVOICE CHECK: PASS")

    # ---------------------------------------------------------
    # 8. Cancel invoice
    # ---------------------------------------------------------
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/cancel",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    cancelled = response.json()

    assert cancelled["id"] == invoice_id
    assert cancelled["status"] == "CANCELLED"

    print("CANCEL INVOICE: PASS")

    # ---------------------------------------------------------
    # 9. Verify final state
    # ---------------------------------------------------------
    response = client.get(
        f"/api/v1/invoices/{invoice_id}",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    final_invoice = response.json()

    assert final_invoice["status"] == "CANCELLED"
    assert final_invoice["total"] == 15000

    print("FINAL INVOICE STATE: PASS")

    # ---------------------------------------------------------
    # 10. Inventory must still be unchanged
    # ---------------------------------------------------------
    response = client.get(
        f"/api/v1/products/{product_id}",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    final_product = response.json()

    assert final_product["quantity"] == 20

    print("FINAL INVENTORY INTEGRITY: PASS")

    print()
    print("============================================================")
    print(" INVOICE INTEGRATION TEST: PASS")
    print("============================================================")


if __name__ == "__main__":
    test_invoice_complete_workflow()
