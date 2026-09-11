import asyncio
import uuid

import httpx

from main import app


async def run_test():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:

        print("=" * 80)
        print("IMRAN BUSINESS OS")
        print("SALES + PURCHASES CANCELLATION INTEGRATION TEST")
        print("=" * 80)

        unique = uuid.uuid4().hex[:10]

        # ----------------------------------------------------
        # BUSINESS A
        # ----------------------------------------------------

        email_a = f"cancel_a_{unique}@example.com"

        register_a = {
            "name": "Cancellation Business A",
            "email": email_a,
            "password": "TestPassword123!",
            "business_name": "Cancellation Business A",
            "business_category": "RETAIL",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en",
        }

        response = await client.post(
            "/api/v1/auth/register",
            json=register_a,
        )

        assert response.status_code in (200, 201), response.text

        data = response.json()

        token_a = data.get("access_token")

        assert token_a, data

        headers_a = {
            "Authorization": f"Bearer {token_a}"
        }

        print("[1] BUSINESS A REGISTRATION: PASS")

        # ----------------------------------------------------
        # BUSINESS B
        # ----------------------------------------------------

        email_b = f"cancel_b_{unique}@example.com"

        register_b = {
            "name": "Cancellation Business B",
            "email": email_b,
            "password": "TestPassword123!",
            "business_name": "Cancellation Business B",
            "business_category": "RETAIL",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en",
        }

        response = await client.post(
            "/api/v1/auth/register",
            json=register_b,
        )

        assert response.status_code in (200, 201), response.text

        token_b = response.json().get("access_token")

        assert token_b

        headers_b = {
            "Authorization": f"Bearer {token_b}"
        }

        print("[2] BUSINESS B REGISTRATION: PASS")

        # ----------------------------------------------------
        # CREATE PRODUCT
        # ----------------------------------------------------

        product_response = await client.post(
            "/api/v1/products",
            headers=headers_a,
            json={
                "name": "Cancellation Test Product",
                "sku": f"CANCEL-{unique}",
                "type": "PRODUCT",
                "price": 1000,
                "cost": 500,
            },
        )

        assert product_response.status_code in (200, 201), (
            product_response.text
        )

        product = product_response.json()
        product_id = product["id"]

        print("[3] PRODUCT CREATE: PASS")

        # ----------------------------------------------------
        # CREATE SUPPLIER
        # ----------------------------------------------------

        supplier_response = await client.post(
            "/api/v1/suppliers",
            headers=headers_a,
            json={
                "name": "Cancellation Supplier",
                "phone": "0999000000",
                "email": f"supplier_{unique}@example.com",
                "address": "Lilongwe",
            },
        )

        assert supplier_response.status_code in (200, 201), (
            supplier_response.text
        )

        supplier_id = supplier_response.json()["id"]

        print("[4] SUPPLIER CREATE: PASS")

        # ----------------------------------------------------
        # PURCHASE 10 UNITS
        # ----------------------------------------------------

        purchase_response = await client.post(
            "/api/v1/purchases",
            headers=headers_a,
            json={
                "supplier_id": supplier_id,
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 10,
                        "unit_cost": 500,
                    }
                ],
            },
        )

        assert purchase_response.status_code in (200, 201), (
            purchase_response.text
        )

        purchase = purchase_response.json()
        purchase_id = purchase["id"]

        assert purchase["total"] == 5000

        print("[5] PURCHASE CREATE + CALCULATION: PASS")

        # ----------------------------------------------------
        # STOCK SHOULD BE 10
        # ----------------------------------------------------

        product_response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers_a,
        )

        assert product_response.status_code == 200

        stock = product_response.json()["quantity"]

        assert float(stock) == 10

        print("[6] PURCHASE STOCK = 10: PASS")

        # ----------------------------------------------------
        # CANCEL PURCHASE
        # ----------------------------------------------------

        cancel_purchase = await client.post(
            f"/api/v1/purchases/{purchase_id}/cancel",
            headers=headers_a,
        )

        assert cancel_purchase.status_code == 200, (
            cancel_purchase.text
        )

        cancel_data = cancel_purchase.json()

        assert cancel_data["status"] == "CANCELLED"

        print("[7] PURCHASE CANCELLATION: PASS")

        # ----------------------------------------------------
        # STOCK SHOULD RETURN TO ZERO
        # ----------------------------------------------------

        product_response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers_a,
        )

        assert product_response.status_code == 200

        stock = product_response.json()["quantity"]

        assert float(stock) == 0

        print("[8] PURCHASE CANCELLATION → STOCK = 0: PASS")

        # ----------------------------------------------------
        # SECOND PURCHASE FOR SALE TEST
        # ----------------------------------------------------

        purchase_response = await client.post(
            "/api/v1/purchases",
            headers=headers_a,
            json={
                "supplier_id": supplier_id,
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 10,
                        "unit_cost": 500,
                    }
                ],
            },
        )

        assert purchase_response.status_code in (200, 201), (
            purchase_response.text
        )

        print("[9] SECOND PURCHASE = 10 STOCK: PASS")

        # ----------------------------------------------------
        # CREATE SALE FOR 4 UNITS
        # ----------------------------------------------------

        sale_response = await client.post(
            "/api/v1/sales",
            headers=headers_a,
            json={
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 4,
                        "unit_price": 1000,
                    }
                ],
            },
        )

        assert sale_response.status_code in (200, 201), (
            sale_response.text
        )

        sale = sale_response.json()
        sale_id = sale["id"]

        assert sale["total"] == 4000

        print("[10] SALE CREATE + CALCULATION: PASS")

        # ----------------------------------------------------
        # STOCK SHOULD BE 6
        # ----------------------------------------------------

        product_response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers_a,
        )

        assert product_response.status_code == 200

        stock = product_response.json()["quantity"]

        assert float(stock) == 6

        print("[11] SALE STOCK = 6: PASS")

        # ----------------------------------------------------
        # CANCEL SALE
        # ----------------------------------------------------

        cancel_sale = await client.post(
            f"/api/v1/sales/{sale_id}/cancel",
            headers=headers_a,
        )

        assert cancel_sale.status_code == 200, (
            cancel_sale.text
        )

        cancel_data = cancel_sale.json()

        assert cancel_data["status"] == "CANCELLED"

        print("[12] SALE CANCELLATION: PASS")

        # ----------------------------------------------------
        # STOCK SHOULD RETURN TO 10
        # ----------------------------------------------------

        product_response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers_a,
        )

        assert product_response.status_code == 200

        stock = product_response.json()["quantity"]

        assert float(stock) == 10

        print("[13] SALE CANCELLATION → STOCK = 10: PASS")

        # ----------------------------------------------------
        # DOUBLE SALE CANCELLATION
        # ----------------------------------------------------

        second_cancel = await client.post(
            f"/api/v1/sales/{sale_id}/cancel",
            headers=headers_a,
        )

        assert second_cancel.status_code == 400

        assert "already cancelled" in (
            second_cancel.text.lower()
        )

        print("[14] DOUBLE SALE CANCELLATION BLOCKED: PASS")

        # ----------------------------------------------------
        # DOUBLE PURCHASE CANCELLATION
        # ----------------------------------------------------

        cancelled_purchase_id = purchase_id

        second_purchase_cancel = await client.post(
            f"/api/v1/purchases/{cancelled_purchase_id}/cancel",
            headers=headers_a,
        )

        assert second_purchase_cancel.status_code == 400

        assert "already cancelled" in (
            second_purchase_cancel.text.lower()
        )

        print("[15] DOUBLE PURCHASE CANCELLATION BLOCKED: PASS")

        # ----------------------------------------------------
        # TENANT ISOLATION — SALE
        # ----------------------------------------------------

        cross_sale = await client.post(
            f"/api/v1/sales/{sale_id}/cancel",
            headers=headers_b,
        )

        assert cross_sale.status_code == 404

        print("[16] CROSS-TENANT SALE CANCELLATION BLOCKED: PASS")

        # ----------------------------------------------------
        # TENANT ISOLATION — PURCHASE
        # ----------------------------------------------------

        cross_purchase = await client.post(
            f"/api/v1/purchases/{purchase_id}/cancel",
            headers=headers_b,
        )

        assert cross_purchase.status_code == 404

        print(
            "[17] CROSS-TENANT PURCHASE CANCELLATION "
            "BLOCKED: PASS"
        )

        # ----------------------------------------------------
        # UNAUTHENTICATED
        # ----------------------------------------------------

        unauth_sale = await client.post(
            f"/api/v1/sales/{sale_id}/cancel",
        )

        assert unauth_sale.status_code in (401, 403)

        unauth_purchase = await client.post(
            f"/api/v1/purchases/{purchase_id}/cancel",
        )

        assert unauth_purchase.status_code in (401, 403)

        print("[18] UNAUTHENTICATED CANCELLATION BLOCKED: PASS")

        # ----------------------------------------------------
        # AUDIT LOGS
        # ----------------------------------------------------

        audit_response = await client.get(
            "/api/v1/audit-logs",
            headers=headers_a,
        )

        assert audit_response.status_code == 200, (
            audit_response.text
        )

        audit_text = audit_response.text

        assert "SALE" in audit_text
        assert "PURCHASE" in audit_text
        assert "CANCEL" in audit_text

        print("[19] CANCELLATION AUDIT LOGS: PASS")

        print()
        print("=" * 80)
        print("SALES + PURCHASES CANCELLATION TEST: PASS")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_test())
