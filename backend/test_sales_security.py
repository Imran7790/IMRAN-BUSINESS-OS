import asyncio
import uuid

import httpx

from main import app


BASE = "http://test"


async def main():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url=BASE,
    ) as client:

        print("=" * 60)
        print(" IMRAN BUSINESS OS")
        print(" SALES API SECURITY + CALCULATION + AUDIT TEST")
        print("=" * 60)

        # --------------------------------------------------
        # 1. Register Business A
        # --------------------------------------------------
        print("[1] Registering Business A...")

        suffix_a = uuid.uuid4().hex[:8]

        payload_a = {
            "name": "Sales Tester A",
            "email": f"sales_a_{suffix_a}@example.com",
            "password": "TestPassword123!",
            "business_name": f"Sales Business A {suffix_a}",
            "business_category": "retail",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en",
        }

        response = await client.post(
            "/api/v1/auth/register",
            json=payload_a,
        )

        if response.status_code not in (200, 201):
            raise SystemExit(
                f"BUSINESS A REGISTRATION FAILED: "
                f"{response.status_code} {response.text}"
            )

        data_a = response.json()
        token_a = data_a["access_token"]

        headers_a = {
            "Authorization": f"Bearer {token_a}"
        }

        print("BUSINESS A REGISTRATION: PASS")

        # --------------------------------------------------
        # 2. Register Business B
        # --------------------------------------------------
        print("[2] Registering Business B...")

        suffix_b = uuid.uuid4().hex[:8]

        payload_b = {
            "name": "Sales Tester B",
            "email": f"sales_b_{suffix_b}@example.com",
            "password": "TestPassword123!",
            "business_name": f"Sales Business B {suffix_b}",
            "business_category": "retail",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en",
        }

        response = await client.post(
            "/api/v1/auth/register",
            json=payload_b,
        )

        if response.status_code not in (200, 201):
            raise SystemExit(
                f"BUSINESS B REGISTRATION FAILED: "
                f"{response.status_code} {response.text}"
            )

        data_b = response.json()
        token_b = data_b["access_token"]

        headers_b = {
            "Authorization": f"Bearer {token_b}"
        }

        print("BUSINESS B REGISTRATION: PASS")

        # --------------------------------------------------
        # 3. Create product in Business A
        # --------------------------------------------------
        print("[3] Creating products in Business A...")

        product_1 = await client.post(
            "/api/v1/products",
            headers=headers_a,
            json={
                "name": "Test Product 1",
                "sku": f"SALE-A-{suffix_a}-1",
                "type": "PRODUCT",
                "price": 1000,
                "cost": 600,
                "quantity": 100,
            },
        )

        if product_1.status_code not in (200, 201):
            raise SystemExit(
                f"PRODUCT 1 CREATE FAILED: "
                f"{product_1.status_code} {product_1.text}"
            )

        product_1_id = product_1.json()["id"]

        product_2 = await client.post(
            "/api/v1/products",
            headers=headers_a,
            json={
                "name": "Test Product 2",
                "sku": f"SALE-A-{suffix_a}-2",
                "type": "PRODUCT",
                "price": 2500,
                "cost": 1500,
                "quantity": 100,
            },
        )

        if product_2.status_code not in (200, 201):
            raise SystemExit(
                f"PRODUCT 2 CREATE FAILED: "
                f"{product_2.status_code} {product_2.text}"
            )

        product_2_id = product_2.json()["id"]

        print("PRODUCT CREATE: PASS")

        # --------------------------------------------------
        # 4. Create customer in Business A
        # --------------------------------------------------
        print("[4] Creating customer in Business A...")

        customer = await client.post(
            "/api/v1/customers",
            headers=headers_a,
            json={
                "name": "Sales Customer A",
                "phone": f"099{suffix_a[:7]}",
                "email": f"customer_{suffix_a}@example.com",
                "address": "Lilongwe",
            },
        )

        if customer.status_code not in (200, 201):
            raise SystemExit(
                f"CUSTOMER CREATE FAILED: "
                f"{customer.status_code} {customer.text}"
            )

        customer_id = customer.json()["id"]

        print("CUSTOMER CREATE: PASS")

        # --------------------------------------------------
        # 5. Create sale
        # Product 1: 2 x 1000 = 2000
        # Product 2: 3 x 2500 = 7500
        # Expected total = 9500
        # --------------------------------------------------
        print("[5] Creating sale in Business A...")

        sale_response = await client.post(
            "/api/v1/sales",
            headers=headers_a,
            json={
                "customer_id": customer_id,
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_1_id,
                        "quantity": 2,
                    },
                    {
                        "product_id": product_2_id,
                        "quantity": 3,
                    },
                ],
            },
        )

        if sale_response.status_code not in (200, 201):
            raise SystemExit(
                f"SALE CREATE FAILED: "
                f"{sale_response.status_code} {sale_response.text}"
            )

        sale = sale_response.json()
        sale_id = sale["id"]

        print("SALE CREATE: PASS")
        print("SALE ID:", sale_id)

        # --------------------------------------------------
        # 6. Verify calculation
        # --------------------------------------------------
        print("[6] Checking sale calculation...")

        if sale["subtotal"] != 9500:
            raise SystemExit(
                f"CALCULATION FAILED: subtotal={sale['subtotal']}"
            )

        if sale["total"] != 9500:
            raise SystemExit(
                f"CALCULATION FAILED: total={sale['total']}"
            )

        if len(sale["items"]) != 2:
            raise SystemExit(
                f"ITEM COUNT FAILED: {len(sale['items'])}"
            )

        print("SALE CALCULATION: PASS")
        print("EXPECTED TOTAL: 9500 MWK")
        print("ACTUAL TOTAL:", sale["total"], "MWK")

        # --------------------------------------------------
        # 7. Business A reads its sale
        # --------------------------------------------------
        print("[7] Business A reading its sale...")

        response = await client.get(
            f"/api/v1/sales/{sale_id}",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"BUSINESS A SALE READ FAILED: "
                f"{response.status_code} {response.text}"
            )

        print("BUSINESS A SALE READ: PASS")

        # --------------------------------------------------
        # 8. Business B attempts cross-tenant read
        # --------------------------------------------------
        print("[8] Business B attempting to read Business A sale...")

        response = await client.get(
            f"/api/v1/sales/{sale_id}",
            headers=headers_b,
        )

        if response.status_code != 404:
            raise SystemExit(
                "SECURITY FAILURE: Business B accessed "
                f"Business A sale: {response.status_code}"
            )

        print("CROSS-TENANT READ PROTECTION: PASS")

        # --------------------------------------------------
        # 9. Business B attempts cross-tenant delete
        # --------------------------------------------------
        print("[9] Business B attempting to delete Business A sale...")

        response = await client.delete(
            f"/api/v1/sales/{sale_id}",
            headers=headers_b,
        )

        if response.status_code != 404:
            raise SystemExit(
                "SECURITY FAILURE: Business B deleted "
                f"Business A sale: {response.status_code}"
            )

        print("CROSS-TENANT DELETE PROTECTION: PASS")

        # --------------------------------------------------
        # 10. Unauthenticated request
        # --------------------------------------------------
        print("[10] Unauthenticated sale request...")

        response = await client.get(
            f"/api/v1/sales/{sale_id}"
        )

        if response.status_code != 401:
            raise SystemExit(
                "AUTH SECURITY FAILURE: "
                f"Unauthenticated request returned {response.status_code}"
            )

        print("UNAUTHENTICATED REQUEST REJECTED: PASS")

        # --------------------------------------------------
        # 11. Sales pagination
        # --------------------------------------------------
        print("[11] Testing sales pagination...")

        response = await client.get(
            "/api/v1/sales?limit=10&offset=0",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"SALES PAGINATION FAILED: "
                f"{response.status_code} {response.text}"
            )

        listing = response.json()

        if listing["total"] < 1:
            raise SystemExit("SALES PAGINATION FAILED: total < 1")

        if not isinstance(listing["items"], list):
            raise SystemExit("SALES PAGINATION FAILED: items is not a list")

        print("SALES PAGINATION: PASS")

        # --------------------------------------------------
        # 12. Invalid quantity
        # --------------------------------------------------
        print("[12] Testing invalid quantity protection...")

        response = await client.post(
            "/api/v1/sales",
            headers=headers_a,
            json={
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_1_id,
                        "quantity": 0,
                    }
                ],
            },
        )

        if response.status_code != 400:
            raise SystemExit(
                "INVALID QUANTITY TEST FAILED: "
                f"{response.status_code} {response.text}"
            )

        print("INVALID QUANTITY REJECTED: PASS")

        # --------------------------------------------------
        # 13. Invalid product
        # --------------------------------------------------
        print("[13] Testing invalid product protection...")

        response = await client.post(
            "/api/v1/sales",
            headers=headers_a,
            json={
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": str(uuid.uuid4()),
                        "quantity": 1,
                    }
                ],
            },
        )

        if response.status_code != 404:
            raise SystemExit(
                "INVALID PRODUCT TEST FAILED: "
                f"{response.status_code} {response.text}"
            )

        print("INVALID PRODUCT REJECTED: PASS")

        # --------------------------------------------------
        # 14. Audit CREATE
        # --------------------------------------------------
        print("[14] Checking CREATE audit...")

        response = await client.get(
            "/api/v1/audit-logs?limit=100&offset=0",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"AUDIT READ FAILED: "
                f"{response.status_code} {response.text}"
            )

        audit_data = response.json()

        logs = audit_data.get("items", [])

        create_sale_logs = [
            log for log in logs
            if log.get("entity_type") == "SALE"
            and log.get("entity_id") == sale_id
            and log.get("action") == "CREATE"
        ]

        if not create_sale_logs:
            raise SystemExit("CREATE AUDIT FAILED")

        print("CREATE AUDIT: PASS")

        # --------------------------------------------------
        # 15. Business B audit isolation
        # --------------------------------------------------
        print("[15] Business B checking audit logs...")

        response = await client.get(
            "/api/v1/audit-logs?limit=100&offset=0",
            headers=headers_b,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"BUSINESS B AUDIT READ FAILED: "
                f"{response.status_code} {response.text}"
            )

        b_logs = response.json().get("items", [])

        leaked = [
            log for log in b_logs
            if log.get("entity_id") == sale_id
        ]

        if leaked:
            raise SystemExit(
                "SECURITY FAILURE: Business B received Business A sale audit"
            )

        print("AUDIT TENANT ISOLATION: PASS")

        # --------------------------------------------------
        # 16. Delete sale
        # --------------------------------------------------
        print("[16] Business A deleting sale...")

        response = await client.delete(
            f"/api/v1/sales/{sale_id}",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"SALE DELETE FAILED: "
                f"{response.status_code} {response.text}"
            )

        print("SALE DELETE: PASS")

        # --------------------------------------------------
        # 17. Verify DELETE audit
        # --------------------------------------------------
        print("[17] Checking DELETE audit...")

        response = await client.get(
            "/api/v1/audit-logs?limit=100&offset=0",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"AUDIT READ AFTER DELETE FAILED: "
                f"{response.status_code} {response.text}"
            )

        logs = response.json().get("items", [])

        delete_sale_logs = [
            log for log in logs
            if log.get("entity_type") == "SALE"
            and log.get("entity_id") == sale_id
            and log.get("action") == "DELETE"
        ]

        if not delete_sale_logs:
            raise SystemExit("DELETE AUDIT FAILED")

        print("DELETE AUDIT: PASS")

        # --------------------------------------------------
        # FINAL
        # --------------------------------------------------
        print("=" * 60)
        print(" SALES API SECURITY + CALCULATION + AUDIT TEST: PASS")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
