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
            "name": "Payment Test Owner",
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


def test_payment_complete_workflow():
    token, business_id = register_business(
        "Payment Integration Business",
        unique_email("payment"),
    )

    auth = headers(token)

    # ---------------------------------------------------------
    # 1. Create customer
    # ---------------------------------------------------------
    response = client.post(
        "/api/v1/customers",
        headers=auth,
        json={
            "name": "Payment Test Customer",
            "phone": "+265999000002",
            "email": "payment-customer@test.local",
            "address": "Lilongwe",
        },
    )

    assert response.status_code in (200, 201), response.text

    customer = response.json()
    customer_id = customer["id"]

    print("CREATE CUSTOMER: PASS")

    # ---------------------------------------------------------
    # 2. Create product
    # ---------------------------------------------------------
    response = client.post(
        "/api/v1/products",
        headers=auth,
        json={
            "name": "Payment Test Product",
            "sku": "PAY-TEST-001",
            "type": "product",
            "price": 10000,
            "cost": 6000,
            "quantity": 20,
        },
    )

    assert response.status_code in (200, 201), response.text

    product = response.json()
    product_id = product["id"]

    print("CREATE PRODUCT: PASS")

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
                    "description": "Payment Test Product",
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
    print("INVOICE TOTAL:", invoice["total"])

    # ---------------------------------------------------------
    # 4. Issue invoice
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
    # 5. First payment: MWK 5,000
    # ---------------------------------------------------------
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers=auth,
        json={
            "amount": 5000,
            "payment_method": "CASH",
            "reference": "PAY-001",
            "notes": "First payment",
        },
    )

    assert response.status_code == 201, response.text

    payment_one = response.json()

    assert payment_one["invoice_id"] == invoice_id
    assert payment_one["business_id"] == business_id
    assert payment_one["amount"] == 5000
    assert payment_one["currency_code"] == "MWK"
    assert payment_one["payment_method"] == "CASH"

    print("FIRST PAYMENT: PASS")

    # ---------------------------------------------------------
    # 6. Verify partial payment state
    # ---------------------------------------------------------
    response = client.get(
        f"/api/v1/invoices/{invoice_id}",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    partial = response.json()

    assert partial["status"] == "PARTIALLY_PAID"
    assert partial["amount_paid"] == 5000
    assert partial["balance_due"] == 10000

    print("PARTIAL PAYMENT STATE: PASS")
    print("AMOUNT PAID:", partial["amount_paid"])
    print("BALANCE DUE:", partial["balance_due"])

    # ---------------------------------------------------------
    # 7. Second payment: MWK 10,000
    # ---------------------------------------------------------
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers=auth,
        json={
            "amount": 10000,
            "payment_method": "BANK",
            "reference": "PAY-002",
            "notes": "Final payment",
        },
    )

    assert response.status_code == 201, response.text

    payment_two = response.json()

    assert payment_two["invoice_id"] == invoice_id
    assert payment_two["business_id"] == business_id
    assert payment_two["amount"] == 10000
    assert payment_two["currency_code"] == "MWK"
    assert payment_two["payment_method"] == "BANK"

    print("SECOND PAYMENT: PASS")

    # ---------------------------------------------------------
    # 8. Verify fully paid state
    # ---------------------------------------------------------
    response = client.get(
        f"/api/v1/invoices/{invoice_id}",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    paid = response.json()

    assert paid["status"] == "PAID"
    assert paid["amount_paid"] == 15000
    assert paid["balance_due"] == 0

    print("FULL PAYMENT STATE: PASS")
    print("AMOUNT PAID:", paid["amount_paid"])
    print("BALANCE DUE:", paid["balance_due"])

    # ---------------------------------------------------------
    # 9. Verify payment list
    # ---------------------------------------------------------
    response = client.get(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    payment_list = response.json()

    assert payment_list["invoice_id"] == invoice_id
    assert payment_list["currency_code"] == "MWK"
    assert payment_list["invoice_total"] == 15000
    assert payment_list["amount_paid"] == 15000
    assert payment_list["balance_due"] == 0
    assert payment_list["invoice_status"] == "PAID"
    assert len(payment_list["payments"]) == 2

    assert payment_list["payments"][0]["amount"] == 5000
    assert payment_list["payments"][1]["amount"] == 10000

    print("PAYMENT LIST: PASS")

    # ---------------------------------------------------------
    # 10. Overpayment must be rejected
    # ---------------------------------------------------------
    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        headers=auth,
        json={
            "amount": 1,
            "payment_method": "CASH",
            "reference": "OVERPAY-001",
        },
    )

    assert response.status_code == 400, response.text

    print("OVERPAYMENT BLOCKED: PASS")

    # ---------------------------------------------------------
    # 11. Verify audit records
    # ---------------------------------------------------------
    response = client.get(
        "/api/v1/audit-logs",
        headers=auth,
    )

    assert response.status_code == 200, response.text

    audit_data = response.json()

    if isinstance(audit_data, dict):
        audit_items = (
            audit_data.get("items")
            or audit_data.get("logs")
            or audit_data.get("data")
            or []
        )
    else:
        audit_items = audit_data

    payment_audits = [
        item
        for item in audit_items
        if item.get("action") == "PAYMENT_CREATED"
        and item.get("entity_type") == "payment"
    ]

    assert len(payment_audits) >= 2

    print("PAYMENT AUDIT LOGS: PASS")

    print()
    print("============================================================")
    print("PAYMENT INTEGRATION TEST: PASS")
    print("============================================================")
