from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient

from main import app
from app.database import SessionLocal
from app.database import SessionLocal
from app.models.core import (
    Business,
    Customer,
    Product,
    Quotation,
    QuotationItem,
    Sale,
    SaleItem,
    StockMovement,
    User,
)

client = TestClient(app)


def register_business(name, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Owner",
            "email": email,
            "password": "StrongPassword123!",
            "business_name": name,
            "business_category": "RETAIL",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en",
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def login(email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "StrongPassword123!",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_customer(token, name):
    response = client.post(
        "/api/v1/customers",
        headers=auth(token),
        json={
            "name": name,
            "phone": "0999000000",
            "email": None,
            "address": "Lilongwe",
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


def create_product(token, name, quantity):
    response = client.post(
        "/api/v1/products",
        headers=auth(token),
        json={
            "name": name,
            "sku": name.upper().replace(" ", "-"),
            "type": "product",
            "price": 5000,
            "cost": 3000,
            "quantity": quantity,
            "reorder_level": 2,
            "target_quantity": 10,
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


def create_quotation(token, customer_id, product_id, quantity=2):
    response = client.post(
        "/api/v1/quotations",
        headers=auth(token),
        json={
            "customer_id": customer_id,
            "valid_until": (date.today() + timedelta(days=7)).isoformat(),
            "discount": 0,
            "tax": 0,
            "notes": "Conversion integration test",
            "items": [
                {
                    "product_id": product_id,
                    "description": "Test product",
                    "quantity": quantity,
                    "unit_price": 5000,
                }
            ],
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def send_quotation(token, quotation_id):
    response = client.post(
        f"/api/v1/quotations/{quotation_id}/send",
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def accept_quotation(token, quotation_id):
    response = client.post(
        f"/api/v1/quotations/{quotation_id}/accept",
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_quotation_conversion():
    email_a = f"conversion_a_{uuid.uuid4().hex[:8]}@example.com"
    email_b = f"conversion_b_{uuid.uuid4().hex[:8]}@example.com"

    register_business("Conversion Business A", email_a)
    register_business("Conversion Business B", email_b)

    token_a = login(email_a)
    token_b = login(email_b)

    customer_a = create_customer(token_a, "Customer A")
    product_a = create_product(token_a, "Product A", 10)

    quotation = create_quotation(
        token_a,
        customer_a,
        product_a,
        quantity=2,
    )

    quotation_id = quotation["id"]

    print("[1] QUOTATION CREATED: PASS")

    send_quotation(token_a, quotation_id)
    print("[2] QUOTATION SENT: PASS")

    accepted = accept_quotation(token_a, quotation_id)
    assert accepted["status"] == "ACCEPTED"
    print("[3] QUOTATION ACCEPTED: PASS")

    converted = client.post(
        f"/api/v1/quotations/{quotation_id}/convert-to-sale",
        headers=auth(token_a),
    )

    assert converted.status_code == 200, converted.text
    sale = converted.json()

    assert sale["customer_id"] == customer_a
    assert sale["currency_code"] == "MWK"
    assert sale["total"] == 10000
    assert sale["status"] == "COMPLETED"
    assert len(sale["items"]) == 1
    assert sale["items"][0]["product_id"] == product_a
    assert sale["items"][0]["quantity"] == 2
    assert sale["items"][0]["unit_price"] == 5000

    print("[4] CONVERTED TO SALE: PASS")
    print("[5] SALE TOTAL/ITEMS: PASS")

    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_a).first()
        assert product is not None
        assert float(product.quantity) == 8

        quotation_db = (
            db.query(Quotation)
            .filter(Quotation.id == quotation_id)
            .first()
        )
        assert quotation_db.status == "CONVERTED"

        sale_db = db.query(Sale).filter(Sale.id == sale["id"]).first()
        assert sale_db is not None

        sale_item = (
            db.query(SaleItem)
            .filter(SaleItem.sale_id == sale["id"])
            .first()
        )
        assert sale_item is not None

        movement = (
            db.query(StockMovement)
            .filter(
                StockMovement.product_id == product_a,
                StockMovement.reference_id == sale["id"],
            )
            .first()
        )
        assert movement is not None
        assert movement.movement_type == "SALE"
        assert float(movement.quantity) == 2

        print("[6] STOCK DEDUCTION: PASS")
        print("[7] STOCK MOVEMENT: PASS")
        print("[8] QUOTATION STATUS CONVERTED: PASS")
    finally:
        db.close()

    duplicate = client.post(
        f"/api/v1/quotations/{quotation_id}/convert-to-sale",
        headers=auth(token_a),
    )

    assert duplicate.status_code == 409
    print("[9] DUPLICATE CONVERSION BLOCKED: PASS")

    cross_tenant = client.post(
        f"/api/v1/quotations/{quotation_id}/convert-to-sale",
        headers=auth(token_b),
    )

    assert cross_tenant.status_code == 404
    print("[10] CROSS-TENANT CONVERSION BLOCKED: PASS")

    print("QUOTATION CONVERSION INTEGRATION TEST: PASS")

def test_quotation_conversion_insufficient_stock_rolls_back():
    from app.models.core import Sale, SaleItem, StockMovement, AuditLog

    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Rollback Owner",
            "email": f"rollback_owner_{uuid.uuid4().hex[:8]}@example.com",
            "password": "StrongPass123!",
            "business_name": "Rollback Business 20260910",
            "business_category": "RETAIL",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en",
        },
    )
    assert register.status_code in (200, 201)

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "rollback_owner_20260910@example.com",
            "password": "StrongPass123!",
        },
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    customer = client.post(
        "/api/v1/customers",
        json={
            "name": "Rollback Customer",
            "phone": "+265888000001",
        },
        headers=headers,
    )
    assert customer.status_code in (200, 201)
    customer_id = customer.json()["id"]

    product = client.post(
        "/api/v1/products",
        json={
            "name": "Rollback Product",
            "sku": "ROLLBACK-001",
            "type": "product",
            "price": 5000,
            "cost": 3000,
            "quantity": 1,
        },
        headers=headers,
    )
    assert product.status_code in (200, 201)
    product_id = product.json()["id"]

    quotation = client.post(
        "/api/v1/quotations",
        json={
            "customer_id": customer_id,
            "valid_until": "2099-12-31",
            "discount": 0,
            "tax": 0,
            "notes": "Insufficient stock rollback test",
            "items": [
                {
                    "product_id": product_id,
                    "description": "Rollback Product",
                    "quantity": 2,
                    "unit_price": 5000,
                }
            ],
        },
        headers=headers,
    )
    assert quotation.status_code in (200, 201)
    quotation_id = quotation.json()["id"]

    sent = client.post(
        f"/api/v1/quotations/{quotation_id}/send",
        headers=headers,
    )
    assert sent.status_code == 200

    accepted = client.post(
        f"/api/v1/quotations/{quotation_id}/accept",
        headers=headers,
    )
    assert accepted.status_code == 200

    with SessionLocal() as db:
        before_sales = {
            sale.id
            for sale in db.query(Sale)
            .filter(Sale.business_id == quotation.json()["business_id"])
            .all()
        }

        before_movements = db.query(StockMovement).count()

    conversion = client.post(
        f"/api/v1/quotations/{quotation_id}/convert-to-sale",
        headers=headers,
    )

    assert conversion.status_code == 400
    assert "Insufficient stock" in conversion.json()["detail"]

    with SessionLocal() as db:
        product_db = db.query(Product).filter(Product.id == product_id).first()
        quotation_db = db.query(Quotation).filter(Quotation.id == quotation_id).first()

        after_sales = {
            sale.id
            for sale in db.query(Sale)
            .filter(Sale.business_id == quotation.json()["business_id"])
            .all()
        }

        after_movements = db.query(StockMovement).count()

        conversion_audits = (
            db.query(AuditLog)
            .filter(
                AuditLog.business_id == quotation.json()["business_id"],
                AuditLog.entity_id == quotation_id,
                AuditLog.action == "QUOTATION_CONVERTED",
            )
            .count()
        )

        assert product_db is not None
        assert product_db.quantity == 1

        assert quotation_db is not None
        assert quotation_db.status == "ACCEPTED"

        assert after_sales == before_sales
        assert after_movements == before_movements
        assert conversion_audits == 0

        sale_items = (
            db.query(SaleItem)
            .filter(SaleItem.sale_id.in_(after_sales))
            .count()
        )
        assert sale_items == 0

    print("[11] INSUFFICIENT STOCK ROLLBACK: PASS")
