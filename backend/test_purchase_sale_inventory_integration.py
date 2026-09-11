import sys

sys.path.insert(0, ".")

import asyncio

import httpx

from main import app


async def main():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:

        print("=" * 70)
        print("IMRAN BUSINESS OS")
        print("PURCHASE ↔ INVENTORY ↔ SALES INTEGRATION TEST")
        print("=" * 70)

        # ------------------------------------------------------------
        # 1. Register business
        # ------------------------------------------------------------
        register = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Integration Owner",
                "email": "inventory.integration.00735e78@example.com",
                "password": "IntegrationPassword123!",
                "business_name": "Integration Business",
                "business_category": "RETAIL",
                "country_code": "MW",
                "currency_code": "MWK",
                "timezone": "Africa/Blantyre",
                "language_code": "en",
            },
        )

        assert register.status_code in (200, 201), register.text
        token = register.json()["access_token"]

        headers = {
            "Authorization": f"Bearer {token}"
        }

        print("[1] BUSINESS REGISTRATION PASS")

        # ------------------------------------------------------------
        # 2. Create product
        # ------------------------------------------------------------
        product_response = await client.post(
            "/api/v1/products",
            headers=headers,
            json={
                "name": "Integration Product",
                "sku": "INT-001",
                "type": "PRODUCT",
                "price": 1500,
                "cost": 1000,
            },
        )

        assert product_response.status_code == 200, product_response.text

        product = product_response.json()
        product_id = product["id"]

        print("[2] PRODUCT CREATE PASS")

        # ------------------------------------------------------------
        # 3. Confirm initial stock = 0
        # ------------------------------------------------------------
        product_response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers,
        )

        assert product_response.status_code == 200, product_response.text

        initial_stock = product_response.json()["quantity"]

        assert float(initial_stock) == 0

        print("[3] INITIAL STOCK = 0 PASS")

        # ------------------------------------------------------------
        # 4. Create PURCHASE for 10 units
        # ------------------------------------------------------------
        purchase_response = await client.post(
            "/api/v1/purchases",
            headers=headers,
            json={
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 10,
                        "unit_cost": 1000,
                    }
                ],
            },
        )

        assert purchase_response.status_code == 200, purchase_response.text

        purchase = purchase_response.json()
        purchase_id = purchase["id"]

        assert purchase["total"] == 10000

        print("[4] PURCHASE CREATE + CALCULATION PASS")

        # ------------------------------------------------------------
        # 5. Confirm purchase increased stock
        # ------------------------------------------------------------
        product_response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers,
        )

        assert product_response.status_code == 200, product_response.text

        stock_after_purchase = product_response.json()["quantity"]

        assert float(stock_after_purchase) == 10

        print("[5] PURCHASE → STOCK +10 PASS")

        # ------------------------------------------------------------
        # 6. Confirm PURCHASE stock movement
        # ------------------------------------------------------------
        movements_response = await client.get(
            "/api/v1/inventory/movements",
            headers=headers,
        )

        assert movements_response.status_code == 200

        movements = movements_response.json()

        purchase_movements = [
            movement
            for movement in movements
            if movement["movement_type"] == "PURCHASE"
            and movement["reference_type"] == "PURCHASE"
            and movement["reference_id"] == purchase_id
        ]

        assert len(purchase_movements) == 1

        purchase_movement = purchase_movements[0]

        assert float(purchase_movement["quantity"]) == 10
        assert float(purchase_movement["quantity_before"]) == 0
        assert float(purchase_movement["quantity_after"]) == 10

        print("[6] PURCHASE STOCK LEDGER PASS")

        # ------------------------------------------------------------
        # 7. Create SALE for 4 units
        # ------------------------------------------------------------
        sale_response = await client.post(
            "/api/v1/sales",
            headers=headers,
            json={
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 4,
                        "unit_price": 1500,
                    }
                ],
            },
        )

        assert sale_response.status_code == 200, sale_response.text

        sale = sale_response.json()
        sale_id = sale["id"]

        assert sale["total"] == 6000

        print("[7] SALE CREATE + CALCULATION PASS")

        # ------------------------------------------------------------
        # 8. Confirm sale reduced stock
        # ------------------------------------------------------------
        product_response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers,
        )

        assert product_response.status_code == 200, product_response.text

        stock_after_sale = product_response.json()["quantity"]

        assert float(stock_after_sale) == 6

        print("[8] SALE → STOCK -4 PASS")

        # ------------------------------------------------------------
        # 9. Confirm SALE stock movement
        # ------------------------------------------------------------
        movements_response = await client.get(
            "/api/v1/inventory/movements",
            headers=headers,
        )

        assert movements_response.status_code == 200

        movements = movements_response.json()

        sale_movements = [
            movement
            for movement in movements
            if movement["movement_type"] == "SALE"
            and movement["reference_type"] == "SALE"
            and movement["reference_id"] == sale_id
        ]

        assert len(sale_movements) == 1

        sale_movement = sale_movements[0]

        assert float(sale_movement["quantity"]) == 4
        assert float(sale_movement["quantity_before"]) == 10
        assert float(sale_movement["quantity_after"]) == 6

        print("[9] SALE STOCK LEDGER PASS")

        # ------------------------------------------------------------
        # 10. Attempt sale larger than available stock
        # ------------------------------------------------------------
        failed_sale_response = await client.post(
            "/api/v1/sales",
            headers=headers,
            json={
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 20,
                        "unit_price": 1500,
                    }
                ],
            },
        )

        assert failed_sale_response.status_code == 400
        assert "Insufficient stock" in failed_sale_response.text

        print("[10] INSUFFICIENT STOCK REJECTION PASS")

        # ------------------------------------------------------------
        # 11. Confirm failed sale did NOT alter stock
        # ------------------------------------------------------------
        product_response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers,
        )

        assert product_response.status_code == 200

        final_stock = product_response.json()["quantity"]

        assert float(final_stock) == 6

        print("[11] FAILED SALE ROLLBACK STOCK PASS")

        # ------------------------------------------------------------
        # 12. Confirm failed sale did not create a SALE movement
        # ------------------------------------------------------------
        movements_response = await client.get(
            "/api/v1/inventory/movements",
            headers=headers,
        )

        assert movements_response.status_code == 200

        movements = movements_response.json()

        failed_sale_movements = [
            movement
            for movement in movements
            if movement["movement_type"] == "SALE"
            and float(movement["quantity"]) == 20
        ]

        assert len(failed_sale_movements) == 0

        print("[12] FAILED SALE NO ORPHAN MOVEMENT PASS")

        print()
        print("=" * 70)
        print("PURCHASE ↔ INVENTORY ↔ SALES INTEGRATION TEST: PASS")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
