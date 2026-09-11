import sys
from datetime import datetime

import httpx

sys.path.insert(0, "backend")

from main import app


RUN_ID = datetime.now().strftime("%Y%m%d%H%M%S%f")


async def register(client, name, email):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Supplier Security Owner",
            "business_name": name,
            "business_category": "Retail",
            "country_code": "MW",
            "currency_code": "MWK",
            "timezone": "Africa/Blantyre",
            "language_code": "en",
            "email": email,
            "password": "SupplierTest123!",
        },
    )

    assert response.status_code == 200, response.text
    return response.json()


async def main():
    print("=" * 60)
    print(" IMRAN BUSINESS OS")
    print(" SUPPLIER API SECURITY + AUDIT TEST")
    print("=" * 60)

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:

        print("[1] Registering Business A...")
        a = await register(
            client,
            "Supplier Security A " + RUN_ID,
            f"supplier_a_{RUN_ID}@example.com",
        )
        token_a = a["access_token"]
        business_a = a["business"]["id"]

        print("BUSINESS A REGISTRATION: PASS")

        print("[2] Registering Business B...")
        b = await register(
            client,
            "Supplier Security B " + RUN_ID,
            f"supplier_b_{RUN_ID}@example.com",
        )
        token_b = b["access_token"]
        business_b = b["business"]["id"]

        print("BUSINESS B REGISTRATION: PASS")

        assert business_a != business_b
        print("TENANT SEPARATION: PASS")

        headers_a = {
            "Authorization": f"Bearer {token_a}"
        }

        headers_b = {
            "Authorization": f"Bearer {token_b}"
        }

        print("[3] Creating supplier in Business A...")
        supplier_response = await client.post(
            "/api/v1/suppliers",
            headers=headers_a,
            json={
                "name": "Test Supplier A",
                "phone": "+265888000001",
                "email": f"test_supplier_{RUN_ID}@example.com",
                "address": "Lilongwe",
            },
        )

        assert supplier_response.status_code == 200, supplier_response.text

        supplier = supplier_response.json()
        supplier_id = supplier["id"]

        assert supplier["business_id"] == business_a

        print("SUPPLIER CREATE: PASS")
        print("SUPPLIER ID:", supplier_id)

        print("[4] Business A reading supplier...")
        response = await client.get(
            f"/api/v1/suppliers/{supplier_id}",
            headers=headers_a,
        )

        assert response.status_code == 200, response.text
        assert response.json()["business_id"] == business_a

        print("BUSINESS A SUPPLIER READ: PASS")

        print("[5] Business B attempting to read Business A supplier...")
        response = await client.get(
            f"/api/v1/suppliers/{supplier_id}",
            headers=headers_b,
        )

        assert response.status_code == 404
        print("CROSS-TENANT READ PROTECTION: PASS")

        print("[6] Business B attempting to delete Business A supplier...")
        response = await client.delete(
            f"/api/v1/suppliers/{supplier_id}",
            headers=headers_b,
        )

        assert response.status_code == 404
        print("CROSS-TENANT DELETE PROTECTION: PASS")

        print("[7] Unauthenticated supplier request...")
        response = await client.get("/api/v1/suppliers")

        assert response.status_code == 401
        print("UNAUTHENTICATED REQUEST REJECTED: PASS")

        print("[8] Testing supplier list pagination...")
        response = await client.get(
            "/api/v1/suppliers?limit=10&offset=0",
            headers=headers_a,
        )

        assert response.status_code == 200, response.text

        data = response.json()

        assert "items" in data
        assert "limit" in data
        assert "offset" in data
        assert "total" in data

        assert data["limit"] == 10
        assert data["offset"] == 0
        assert data["total"] >= 1

        print("SUPPLIER PAGINATION: PASS")
        print("TOTAL:", data["total"])

        print("[9] Checking Business A audit logs...")
        response = await client.get(
            "/api/v1/audit-logs?entity_type=SUPPLIER",
            headers=headers_a,
        )

        assert response.status_code == 200, response.text

        logs = response.json()["items"]

        create_logs = [
            log
            for log in logs
            if log["action"] == "CREATE"
            and log["entity_id"] == supplier_id
        ]

        assert create_logs

        create_log = create_logs[0]

        assert create_log["business_id"] == business_a
        assert create_log["entity_type"] == "SUPPLIER"
        assert create_log["entity_id"] == supplier_id

        print("CREATE AUDIT: PASS")
        print("AUDIT BUSINESS ID:", create_log["business_id"])
        print("AUDIT ENTITY ID:", create_log["entity_id"])

        print("[10] Business B checking supplier audit logs...")
        response = await client.get(
            "/api/v1/audit-logs?entity_type=SUPPLIER",
            headers=headers_b,
        )

        assert response.status_code == 200, response.text

        logs_b = response.json()["items"]

        cross_tenant_logs = [
            log
            for log in logs_b
            if log["entity_id"] == supplier_id
        ]

        assert not cross_tenant_logs

        print("AUDIT TENANT ISOLATION: PASS")

        print("[11] Business A deleting supplier...")
        response = await client.delete(
            f"/api/v1/suppliers/{supplier_id}",
            headers=headers_a,
        )

        assert response.status_code == 200, response.text
        print("SUPPLIER DELETE: PASS")

        print("[12] Checking DELETE audit...")
        response = await client.get(
            "/api/v1/audit-logs?entity_type=SUPPLIER",
            headers=headers_a,
        )

        assert response.status_code == 200, response.text

        logs = response.json()["items"]

        delete_logs = [
            log
            for log in logs
            if log["action"] == "DELETE"
            and log["entity_id"] == supplier_id
        ]

        assert delete_logs

        delete_log = delete_logs[0]

        assert delete_log["business_id"] == business_a
        assert delete_log["entity_type"] == "SUPPLIER"
        assert delete_log["entity_id"] == supplier_id

        print("DELETE AUDIT: PASS")

    print("=" * 60)
    print(" SUPPLIER API SECURITY + AUDIT TEST: PASS")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
