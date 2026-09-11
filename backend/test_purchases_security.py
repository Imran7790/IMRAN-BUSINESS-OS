import asyncio
import httpx

from main import app


async def main():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:

        print("=" * 60)
        print(" IMRAN BUSINESS OS")
        print(" PURCHASE API SECURITY + CALCULATION + AUDIT TEST")
        print("=" * 60)

        # --------------------------------------------------
        # 1. Register Business A
        # --------------------------------------------------
        print("[1] Registering Business A...")

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Business A Owner",
                "email": "purchase_a_1788982696@test.com",
                "password": "TestPassword123!",
                "business_name": "Purchase Business A",
                "business_category": "RETAIL",
                "country_code": "MW",
                "currency_code": "MWK",
                "timezone": "Africa/Blantyre",
                "language_code": "en",
            },
        )

        if response.status_code not in (200, 201):
            raise SystemExit(
                f"BUSINESS A REGISTRATION FAILED: "
                f"{response.status_code} {response.text}"
            )

        token_a = response.json()["access_token"]

        print("BUSINESS A REGISTRATION: PASS")

        # --------------------------------------------------
        # 2. Register Business B
        # --------------------------------------------------
        print("[2] Registering Business B...")

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Business B Owner",
                "email": "purchase_b_1788982696@test.com",
                "password": "TestPassword123!",
                "business_name": "Purchase Business B",
                "business_category": "RETAIL",
                "country_code": "MW",
                "currency_code": "MWK",
                "timezone": "Africa/Blantyre",
                "language_code": "en",
            },
        )

        if response.status_code not in (200, 201):
            raise SystemExit(
                f"BUSINESS B REGISTRATION FAILED: "
                f"{response.status_code} {response.text}"
            )

        token_b = response.json()["access_token"]

        print("BUSINESS B REGISTRATION: PASS")

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # --------------------------------------------------
        # 3. Create product in Business A
        # --------------------------------------------------
        print("[3] Creating product in Business A...")

        response = await client.post(
            "/api/v1/products",
            headers=headers_a,
            json={
                "name": "Test Product",
                "sku": "PURCHASE-001",
                "type": "PRODUCT",
                "price": 1500,
                "cost": 1000,
                "quantity": 100,
            },
        )

        if response.status_code not in (200, 201):
            raise SystemExit(
                f"PRODUCT CREATE FAILED: "
                f"{response.status_code} {response.text}"
            )

        product_id = response.json()["id"]

        print("PRODUCT CREATE: PASS")
        print(f"PRODUCT ID: {product_id}")

        # --------------------------------------------------
        # 4. Create supplier in Business A
        # --------------------------------------------------
        print("[4] Creating supplier in Business A...")

        response = await client.post(
            "/api/v1/suppliers",
            headers=headers_a,
            json={
                "name": "Test Supplier",
                "phone": "+265888000001",
                "email": "supplier_purchase@test.com",
                "address": "Lilongwe",
            },
        )

        if response.status_code not in (200, 201):
            raise SystemExit(
                f"SUPPLIER CREATE FAILED: "
                f"{response.status_code} {response.text}"
            )

        supplier_id = response.json()["id"]

        print("SUPPLIER CREATE: PASS")
        print(f"SUPPLIER ID: {supplier_id}")

        # --------------------------------------------------
        # 5. Create purchase
        # --------------------------------------------------
        print("[5] Creating purchase in Business A...")

        response = await client.post(
            "/api/v1/purchases",
            headers=headers_a,
            json={
                "supplier_id": supplier_id,
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 5,
                        "unit_cost": 1000,
                    },
                    {
                        "product_id": product_id,
                        "quantity": 2,
                        "unit_cost": 1000,
                    },
                ],
            },
        )

        if response.status_code not in (200, 201):
            raise SystemExit(
                f"PURCHASE CREATE FAILED: "
                f"{response.status_code} {response.text}"
            )

        purchase = response.json()
        purchase_id = purchase["id"]

        print("PURCHASE CREATE: PASS")
        print(f"PURCHASE ID: {purchase_id}")

        # --------------------------------------------------
        # 6. Calculation
        # --------------------------------------------------
        print("[6] Checking purchase calculation...")

        expected_total = 7000
        actual_total = purchase["total"]

        if actual_total != expected_total:
            raise SystemExit(
                f"PURCHASE CALCULATION FAILED: "
                f"expected {expected_total}, got {actual_total}"
            )

        print("PURCHASE CALCULATION: PASS")
        print(f"EXPECTED TOTAL: {expected_total} MWK")
        print(f"ACTUAL TOTAL: {actual_total} MWK")

        # --------------------------------------------------
        # 7. Business A read
        # --------------------------------------------------
        print("[7] Business A reading its purchase...")

        response = await client.get(
            f"/api/v1/purchases/{purchase_id}",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"BUSINESS A PURCHASE READ FAILED: "
                f"{response.status_code} {response.text}"
            )

        print("BUSINESS A PURCHASE READ: PASS")

        # --------------------------------------------------
        # 8. Cross-tenant read
        # --------------------------------------------------
        print(
            "[8] Business B attempting to read "
            "Business A purchase..."
        )

        response = await client.get(
            f"/api/v1/purchases/{purchase_id}",
            headers=headers_b,
        )

        if response.status_code != 404:
            raise SystemExit(
                f"CROSS-TENANT READ FAILURE: "
                f"expected 404, got {response.status_code}"
            )

        print("CROSS-TENANT READ PROTECTION: PASS")

        # --------------------------------------------------
        # 9. Cross-tenant delete
        # --------------------------------------------------
        print(
            "[9] Business B attempting to delete "
            "Business A purchase..."
        )

        response = await client.delete(
            f"/api/v1/purchases/{purchase_id}",
            headers=headers_b,
        )

        if response.status_code != 404:
            raise SystemExit(
                f"CROSS-TENANT DELETE FAILURE: "
                f"expected 404, got {response.status_code}"
            )

        print("CROSS-TENANT DELETE PROTECTION: PASS")

        # --------------------------------------------------
        # 10. Unauthenticated
        # --------------------------------------------------
        print("[10] Unauthenticated purchase request...")

        response = await client.get(
            f"/api/v1/purchases/{purchase_id}"
        )

        if response.status_code != 401:
            raise SystemExit(
                f"UNAUTHENTICATED REQUEST FAILURE: "
                f"expected 401, got {response.status_code}"
            )

        print("UNAUTHENTICATED REQUEST REJECTED: PASS")

        # --------------------------------------------------
        # 11. Pagination
        # --------------------------------------------------
        print("[11] Testing purchase pagination...")

        response = await client.get(
            "/api/v1/purchases?skip=0&limit=10",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"PAGINATION FAILED: "
                f"{response.status_code} {response.text}"
            )

        print("PURCHASE PAGINATION: PASS")

        # --------------------------------------------------
        # 12. Invalid quantity
        # --------------------------------------------------
        print("[12] Testing invalid quantity protection...")

        response = await client.post(
            "/api/v1/purchases",
            headers=headers_a,
            json={
                "supplier_id": supplier_id,
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 0,
                        "unit_cost": 1000,
                    }
                ],
            },
        )

        if response.status_code != 400:
            raise SystemExit(
                f"INVALID QUANTITY NOT REJECTED: "
                f"{response.status_code} {response.text}"
            )

        print("INVALID QUANTITY REJECTED: PASS")

        # --------------------------------------------------
        # 13. Invalid product
        # --------------------------------------------------
        print("[13] Testing invalid product protection...")

        response = await client.post(
            "/api/v1/purchases",
            headers=headers_a,
            json={
                "supplier_id": supplier_id,
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": "does-not-exist",
                        "quantity": 1,
                        "unit_cost": 1000,
                    }
                ],
            },
        )

        if response.status_code != 404:
            raise SystemExit(
                f"INVALID PRODUCT NOT REJECTED: "
                f"{response.status_code} {response.text}"
            )

        print("INVALID PRODUCT REJECTED: PASS")

        # --------------------------------------------------
        # 14. Invalid supplier
        # --------------------------------------------------
        print("[14] Testing invalid supplier protection...")

        response = await client.post(
            "/api/v1/purchases",
            headers=headers_a,
            json={
                "supplier_id": "does-not-exist",
                "currency_code": "MWK",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 1,
                        "unit_cost": 1000,
                    }
                ],
            },
        )

        if response.status_code != 404:
            raise SystemExit(
                f"INVALID SUPPLIER NOT REJECTED: "
                f"{response.status_code} {response.text}"
            )

        print("INVALID SUPPLIER REJECTED: PASS")

        # --------------------------------------------------
        # 15. Currency mismatch
        # --------------------------------------------------
        print("[15] Testing currency mismatch protection...")

        response = await client.post(
            "/api/v1/purchases",
            headers=headers_a,
            json={
                "supplier_id": supplier_id,
                "currency_code": "USD",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 1,
                        "unit_cost": 1000,
                    }
                ],
            },
        )

        if response.status_code != 400:
            raise SystemExit(
                f"CURRENCY MISMATCH NOT REJECTED: "
                f"{response.status_code} {response.text}"
            )

        print("CURRENCY MISMATCH REJECTED: PASS")

        # --------------------------------------------------
        # 16. CREATE audit
        # --------------------------------------------------
        print("[16] Checking CREATE audit...")

        response = await client.get(
            "/api/v1/audit-logs?entity_type=PURCHASE",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"AUDIT READ FAILED: "
                f"{response.status_code} {response.text}"
            )

        audit_data = response.json()

        if isinstance(audit_data, dict):
            logs = (
                audit_data.get("items")
                or audit_data.get("data")
                or audit_data.get("logs")
                or []
            )
        else:
            logs = audit_data

        create_logs = [
            log for log in logs
            if log.get("action") == "CREATE"
            and log.get("entity_id") == purchase_id
        ]

        if not create_logs:
            raise SystemExit("CREATE AUDIT NOT FOUND")

        print("CREATE AUDIT: PASS")

        # --------------------------------------------------
        # 17. Business B audit isolation
        # --------------------------------------------------
        print(
            "[17] Business B checking purchase audit isolation..."
        )

        response = await client.get(
            "/api/v1/audit-logs?entity_type=PURCHASE",
            headers=headers_b,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"BUSINESS B AUDIT REQUEST FAILED: "
                f"{response.status_code} {response.text}"
            )

        audit_b = response.json()

        if isinstance(audit_b, dict):
            logs_b = (
                audit_b.get("items")
                or audit_b.get("data")
                or audit_b.get("logs")
                or []
            )
        else:
            logs_b = audit_b

        for log in logs_b:
            if log.get("entity_id") == purchase_id:
                raise SystemExit(
                    "SECURITY FAILURE: Business B received "
                    "Business A purchase audit"
                )

        print("AUDIT TENANT ISOLATION: PASS")

        # --------------------------------------------------
        # 18. Delete purchase
        # --------------------------------------------------
        print("[18] Business A deleting purchase...")

        response = await client.delete(
            f"/api/v1/purchases/{purchase_id}",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"PURCHASE DELETE FAILED: "
                f"{response.status_code} {response.text}"
            )

        print("PURCHASE DELETE: PASS")

        # --------------------------------------------------
        # 19. DELETE audit
        # --------------------------------------------------
        print("[19] Checking DELETE audit...")

        response = await client.get(
            "/api/v1/audit-logs?entity_type=PURCHASE",
            headers=headers_a,
        )

        if response.status_code != 200:
            raise SystemExit(
                f"DELETE AUDIT READ FAILED: "
                f"{response.status_code} {response.text}"
            )

        audit_after = response.json()

        if isinstance(audit_after, dict):
            logs_after = (
                audit_after.get("items")
                or audit_after.get("data")
                or audit_after.get("logs")
                or []
            )
        else:
            logs_after = audit_after

        delete_logs = [
            log for log in logs_after
            if log.get("action") == "DELETE"
            and log.get("entity_id") == purchase_id
        ]

        if not delete_logs:
            raise SystemExit("DELETE AUDIT NOT FOUND")

        print("DELETE AUDIT: PASS")

        print("=" * 60)
        print(" PURCHASE API SECURITY + CALCULATION + AUDIT TEST: PASS")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
