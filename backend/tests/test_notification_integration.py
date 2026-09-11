from fastapi.testclient import TestClient
from main import app
import uuid

client = TestClient(app)


def unique_email(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@test.local"


def register_business(name, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Notification Test Owner",
            "email": email,
            "password": "TestPassword123",
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


def create_product(auth, name, quantity, reorder_level, target_quantity):
    response = client.post(
        "/api/v1/products",
        headers=auth,
        json={
            "name": name,
            "sku": f"NOTIF-{uuid.uuid4().hex[:8]}",
            "type": "product",
            "price": 10000,
            "cost": 6000,
            "quantity": quantity,
            "reorder_level": reorder_level,
            "target_quantity": target_quantity,
        },
    )

    assert response.status_code in (200, 201), response.text
    return response.json()


def test_notification_integration():
    print("\n============================================================")
    print(" NOTIFICATION INTEGRATION TEST")
    print("============================================================")

    # 1. Create Business A
    token_a, business_a = register_business(
        "Notification Business A",
        unique_email("notification-a"),
    )
    auth_a = headers(token_a)
    print("[1] BUSINESS A: PASS")

    # 2. Create Business B
    token_b, business_b = register_business(
        "Notification Business B",
        unique_email("notification-b"),
    )
    auth_b = headers(token_b)

    assert business_a != business_b
    print("[2] BUSINESS B: PASS")

    # 3. Create product with stock=10, reorder=5, target=20
    product = create_product(
        auth_a,
        "Notification Test Product",
        quantity=10,
        reorder_level=5,
        target_quantity=20,
    )
    product_id = product["id"]

    assert product["business_id"] == business_a
    print("[3] PRODUCT CREATED: PASS")

    # 4. Reduce stock from 10 -> 5
    # This should create exactly one LOW_STOCK notification.
    response = client.post(
        "/api/v1/inventory/movements",
        headers=auth_a,
        json={
            "product_id": product_id,
            "movement_type": "SALE",
            "quantity": 5,
        },
    )

    assert response.status_code in (200, 201), response.text
    print("[4] STOCK MOVEMENT → LOW STOCK: PASS")

    # 5. Verify unread notification
    response = client.get(
        "/api/v1/notifications?unread=true",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    notifications = response.json()

    low_stock = [
        item for item in notifications
        if item["notification_type"] == "STOCK_LOW"
        and item["entity_id"] == product_id
    ]

    assert len(low_stock) == 1, notifications
    assert low_stock[0]["is_read"] is False
    assert low_stock[0]["severity"] == "WARNING"
    print("[5] LOW STOCK NOTIFICATION: PASS")

    # 6. Repeat movement while still low stock.
    # The unread alert must not be duplicated.
    response = client.post(
        "/api/v1/inventory/movements",
        headers=auth_a,
        json={
            "product_id": product_id,
            "movement_type": "SALE",
            "quantity": 1,
        },
    )

    assert response.status_code in (200, 201), response.text

    response = client.get(
        "/api/v1/notifications?unread=true&notification_type=STOCK_LOW",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    low_notifications = [
        item for item in response.json()
        if item["entity_id"] == product_id
    ]

    assert len(low_notifications) == 1, low_notifications
    print("[6] DUPLICATE LOW-STOCK ALERT BLOCKED: PASS")

    # 7. Verify unread count
    response = client.get(
        "/api/v1/notifications/unread-count",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    assert response.json()["count"] >= 1
    print("[7] UNREAD COUNT: PASS")

    # 8. Mark the low-stock notification as read.
    notification_id = low_notifications[0]["id"]

    response = client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_read"] is True
    print("[8] MARK ONE READ: PASS")

    # 9. Move remaining stock to zero.
    response = client.post(
        "/api/v1/inventory/movements",
        headers=auth_a,
        json={
            "product_id": product_id,
            "movement_type": "SALE",
            "quantity": 4,
        },
    )

    assert response.status_code in (200, 201), response.text
    print("[9] STOCK MOVEMENT → ZERO: PASS")

    # 10. Verify OUT_OF_STOCK notification.
    response = client.get(
        "/api/v1/notifications?unread=true&notification_type=STOCK_OUT",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    out_notifications = [
        item for item in response.json()
        if item["entity_id"] == product_id
    ]

    assert len(out_notifications) == 1, out_notifications
    assert out_notifications[0]["severity"] == "CRITICAL"
    assert out_notifications[0]["is_read"] is False
    print("[10] OUT-OF-STOCK NOTIFICATION: PASS")

    # 11. Business B must not see Business A notifications.
    response = client.get(
        "/api/v1/notifications",
        headers=auth_b,
    )

    assert response.status_code == 200, response.text
    business_b_notifications = response.json()

    assert all(
        item["business_id"] == business_b
        for item in business_b_notifications
    )
    assert all(
        item["entity_id"] != product_id
        for item in business_b_notifications
    )
    print("[11] NOTIFICATION TENANT ISOLATION: PASS")

    # 12. Mark all remaining Business A notifications as read.
    response = client.patch(
        "/api/v1/notifications/read-all",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    print("[12] MARK ALL READ: PASS")

    # 13. Verify no unread notifications remain for this business.
    response = client.get(
        "/api/v1/notifications?unread=true",
        headers=auth_a,
    )

    assert response.status_code == 200, response.text
    assert response.json() == []
    print("[13] ALL NOTIFICATIONS READ: PASS")

    print("============================================================")
    print(" NOTIFICATION INTEGRATION TEST: PASS")
    print("============================================================")


if __name__ == "__main__":
    test_notification_integration()
