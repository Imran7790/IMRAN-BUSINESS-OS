import asyncio
import time
import httpx

from main import app
from app.database import SessionLocal
from app.models.core import AuditLog


async def main():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:

        suffix = str(time.time_ns())

        # ============================================================
        # BUSINESS A
        # ============================================================
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Inventory A User",
                "email": f"inventory_a_{suffix}@example.com",
                "password": "StrongPassword123!",
                "business_name": "Inventory Business A",
                "business_category": "retail",
                "country_code": "MW",
                "currency_code": "MWK",
                "timezone": "Africa/Blantyre",
                "language_code": "en",
            },
        )
        assert response.status_code in (200, 201), response.text
        token_a = response.json()["access_token"]
        print("[1] Business A registration PASS")

        # ============================================================
        # BUSINESS B
        # ============================================================
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Inventory B User",
                "email": f"inventory_b_{suffix}@example.com",
                "password": "StrongPassword123!",
                "business_name": "Inventory Business B",
                "business_category": "retail",
                "country_code": "MW",
                "currency_code": "MWK",
                "timezone": "Africa/Blantyre",
                "language_code": "en",
            },
        )
        assert response.status_code in (200, 201), response.text
        token_b = response.json()["access_token"]
        print("[2] Business B registration PASS")

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # ============================================================
        # PRODUCT
        # ============================================================
        response = await client.post(
            "/api/v1/products",
            headers=headers_a,
            json={
                "name": "Inventory Test Product",
                "sku": f"INV-{suffix}",
                "type": "PRODUCT",
                "price": 1000,
                "cost": 700,
                "quantity": 0,
            },
        )
        assert response.status_code in (200, 201), response.text
        product_id = response.json()["id"]
        print("[3] Product CREATE PASS")

        # ============================================================
        # STOCK IN
        # ============================================================
        response = await client.post(
            "/api/v1/inventory/movements",
            headers=headers_a,
            json={
                "product_id": product_id,
                "movement_type": "PURCHASE",
                "quantity": 10,
                "reference_type": "TEST",
                "reference_id": f"PURCHASE-{suffix}",
            },
        )
        assert response.status_code in (200, 201), response.text
        movement = response.json()

        assert movement["quantity_before"] == 0
        assert movement["quantity_after"] == 10
        assert movement["quantity"] == 10
        assert movement["movement_type"] == "PURCHASE"
        print("[4] STOCK IN + CALCULATION PASS")

        # ============================================================
        # STOCK BALANCE = 10
        # ============================================================
        response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers_a,
        )
        assert response.status_code == 200, response.text
        assert response.json()["quantity"] == 10
        print("[5] STOCK BALANCE AFTER PURCHASE PASS")

        # ============================================================
        # STOCK OUT
        # ============================================================
        response = await client.post(
            "/api/v1/inventory/movements",
            headers=headers_a,
            json={
                "product_id": product_id,
                "movement_type": "SALE",
                "quantity": 3,
                "reference_type": "TEST",
                "reference_id": f"SALE-{suffix}",
            },
        )
        assert response.status_code in (200, 201), response.text
        movement = response.json()

        assert movement["quantity_before"] == 10
        assert movement["quantity_after"] == 7
        assert movement["quantity"] == 3
        assert movement["movement_type"] == "SALE"
        print("[6] STOCK OUT + CALCULATION PASS")

        # ============================================================
        # FINAL BALANCE = 7
        # ============================================================
        response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers_a,
        )
        assert response.status_code == 200
        assert response.json()["quantity"] == 7
        print("[7] FINAL STOCK BALANCE PASS")

        # ============================================================
        # TENANT ISOLATION
        # ============================================================
        response = await client.get(
            f"/api/v1/products/{product_id}",
            headers=headers_b,
        )
        assert response.status_code == 404
        print("[8] CROSS-TENANT PRODUCT ISOLATION PASS")

        response = await client.post(
            "/api/v1/inventory/movements",
            headers=headers_b,
            json={
                "product_id": product_id,
                "movement_type": "PURCHASE",
                "quantity": 100,
            },
        )
        assert response.status_code == 404
        print("[9] CROSS-TENANT INVENTORY ISOLATION PASS")

        # ============================================================
        # AUTHENTICATION
        # ============================================================
        response = await client.get("/api/v1/inventory/movements")
        assert response.status_code in (401, 403)
        print("[10] UNAUTHENTICATED REQUEST REJECTED PASS")

        # ============================================================
        # INVALID MOVEMENT TYPE
        # ============================================================
        response = await client.post(
            "/api/v1/inventory/movements",
            headers=headers_a,
            json={
                "product_id": product_id,
                "movement_type": "INVALID_TYPE",
                "quantity": 1,
            },
        )
        assert response.status_code == 400
        print("[11] INVALID MOVEMENT TYPE REJECTED PASS")

        # ============================================================
        # ZERO QUANTITY
        # ============================================================
        response = await client.post(
            "/api/v1/inventory/movements",
            headers=headers_a,
            json={
                "product_id": product_id,
                "movement_type": "PURCHASE",
                "quantity": 0,
            },
        )
        assert response.status_code == 422
        print("[12] ZERO QUANTITY REJECTED PASS")

        # ============================================================
        # NEGATIVE QUANTITY
        # ============================================================
        response = await client.post(
            "/api/v1/inventory/movements",
            headers=headers_a,
            json={
                "product_id": product_id,
                "movement_type": "PURCHASE",
                "quantity": -5,
            },
        )
        assert response.status_code == 422
        print("[13] NEGATIVE QUANTITY REJECTED PASS")

        # ============================================================
        # INSUFFICIENT STOCK
        # ============================================================
        response = await client.post(
            "/api/v1/inventory/movements",
            headers=headers_a,
            json={
                "product_id": product_id,
                "movement_type": "SALE",
                "quantity": 100,
            },
        )
        assert response.status_code == 400
        print("[14] INSUFFICIENT STOCK REJECTED PASS")

        # ============================================================
        # LIST MOVEMENTS
        # ============================================================
        response = await client.get(
            "/api/v1/inventory/movements",
            headers=headers_a,
        )
        assert response.status_code == 200
        movements = response.json()
        assert len(movements) >= 2
        print("[15] MOVEMENT LIST PASS")

        # ============================================================
        # GET MOVEMENT
        # ============================================================
        movement_id = movements[-1]["id"]

        response = await client.get(
            f"/api/v1/inventory/movements/{movement_id}",
            headers=headers_a,
        )
        assert response.status_code == 200
        assert response.json()["id"] == movement_id
        print("[16] MOVEMENT GET PASS")

        # ============================================================
        # MOVEMENT TENANT ISOLATION
        # ============================================================
        response = await client.get(
            f"/api/v1/inventory/movements/{movement_id}",
            headers=headers_b,
        )
        assert response.status_code == 404
        print("[17] CROSS-TENANT MOVEMENT GET ISOLATION PASS")

    # ================================================================
    # AUDIT LOG
    # ================================================================
    db = SessionLocal()

    try:
        audits = (
            db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "STOCK_MOVEMENT"
            )
            .all()
        )

        assert len(audits) >= 2

        print("[18] INVENTORY AUDIT LOGS PASS")

    finally:
        db.close()

    print()
    print("=" * 70)
    print("INVENTORY API SECURITY + STOCK CALCULATION TEST: PASS")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
