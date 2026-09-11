from datetime import datetime

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)

RUN_ID = datetime.now().strftime("%Y%m%d%H%M%S%f")

email_a = f"audit_a_{RUN_ID}@example.com"
email_b = f"audit_b_{RUN_ID}@example.com"
password = "AuditTest123!"

print("=" * 60)
print(" IMRAN BUSINESS OS")
print(" AUDIT LOG API SECURITY TEST")
print("=" * 60)

# ------------------------------------------------------------
# 1. Register Business A
# ------------------------------------------------------------
print("[1] Registering Business A...")

response_a = client.post(
    "/api/v1/auth/register",
    json={
        "name": "Audit Business A",
        "business_name": "Audit Business A",
        "business_category": "Retail",
        "country_code": "MW",
        "currency_code": "MWK",
        "timezone": "Africa/Blantyre",
        "language_code": "en",
        "email": email_a,
        "password": password,
    },
)

print("STATUS:", response_a.status_code)

if response_a.status_code != 200:
    print("BODY:", response_a.text)
    raise SystemExit("Business A registration failed")

data_a = response_a.json()

token_a = data_a["access_token"]
business_a_id = data_a["business"]["id"]

print("BUSINESS A REGISTRATION: PASS")
print("BUSINESS A ID:", business_a_id)


# ------------------------------------------------------------
# 2. Register Business B
# ------------------------------------------------------------
print("[2] Registering Business B...")

response_b = client.post(
    "/api/v1/auth/register",
    json={
        "name": "Audit Business B",
        "business_name": "Audit Business B",
        "business_category": "Retail",
        "country_code": "MW",
        "currency_code": "MWK",
        "timezone": "Africa/Blantyre",
        "language_code": "en",
        "email": email_b,
        "password": password,
    },
)

print("STATUS:", response_b.status_code)

if response_b.status_code != 200:
    print("BODY:", response_b.text)
    raise SystemExit("Business B registration failed")

data_b = response_b.json()

token_b = data_b["access_token"]
business_b_id = data_b["business"]["id"]

print("BUSINESS B REGISTRATION: PASS")
print("BUSINESS B ID:", business_b_id)


# ------------------------------------------------------------
# 3. Verify different tenants
# ------------------------------------------------------------
print("[3] Verifying tenant IDs...")

if business_a_id == business_b_id:
    raise SystemExit("Business IDs unexpectedly match")

print("TENANT SEPARATION: PASS")


# ------------------------------------------------------------
# 4. Update Business A
# This creates an UPDATE/BUSINESS audit record.
# ------------------------------------------------------------
print("[4] Updating Business A...")

response_update = client.patch(
    "/api/v1/businesses/me",
    headers={
        "Authorization": f"Bearer {token_a}"
    },
    json={
        "name": "Audit Business A Updated"
    },
)

if response_update.status_code != 200:
    print("STATUS:", response_update.status_code)
    print("BODY:", response_update.text)
    raise SystemExit("Business A update failed")

print("BUSINESS UPDATE: PASS")


# ------------------------------------------------------------
# 5. Read Business A audit logs
# ------------------------------------------------------------
print("[5] Reading Business A audit logs...")

response_logs_a = client.get(
    "/api/v1/audit-logs",
    headers={
        "Authorization": f"Bearer {token_a}"
    },
)

if response_logs_a.status_code != 200:
    print("STATUS:", response_logs_a.status_code)
    print("BODY:", response_logs_a.text)
    raise SystemExit("Business A audit read failed")

response_logs_a_data = response_logs_a.json()
logs_a = response_logs_a_data["items"]

print("BUSINESS A AUDIT READ: PASS")
print("AUDIT RECORDS:", len(logs_a))


# ------------------------------------------------------------
# 6. Verify every returned audit belongs to Business A
# ------------------------------------------------------------
print("[6] Checking Business A tenant isolation...")

for log in logs_a:
    if log["business_id"] != business_a_id:
        raise SystemExit(
            "SECURITY FAILURE: Business A received another tenant's audit"
        )

print("BUSINESS A TENANT ISOLATION: PASS")


# ------------------------------------------------------------
# 7. Business B reads its audit logs
# ------------------------------------------------------------
print("[7] Reading Business B audit logs...")

response_logs_b = client.get(
    "/api/v1/audit-logs",
    headers={
        "Authorization": f"Bearer {token_b}"
    },
)

if response_logs_b.status_code != 200:
    print("STATUS:", response_logs_b.status_code)
    print("BODY:", response_logs_b.text)
    raise SystemExit("Business B audit read failed")

response_logs_b_data = response_logs_b.json()
logs_b = response_logs_b_data["items"]

print("BUSINESS B AUDIT READ: PASS")


# ------------------------------------------------------------
# 8. Verify B cannot see A's audit records
# ------------------------------------------------------------
print("[8] Checking cross-tenant audit protection...")

for log in logs_b:
    if log["business_id"] == business_a_id:
        raise SystemExit(
            "SECURITY FAILURE: Business B received Business A audit"
        )

print("CROSS-TENANT AUDIT PROTECTION: PASS")


# ------------------------------------------------------------
# 9. Test audit filters
# ------------------------------------------------------------
print("[9] Testing audit filters...")

response_filter = client.get(
    "/api/v1/audit-logs",
    headers={
        "Authorization": f"Bearer {token_a}"
    },
    params={
        "action": "UPDATE",
        "entity_type": "BUSINESS",
    },
)

if response_filter.status_code != 200:
    print("STATUS:", response_filter.status_code)
    print("BODY:", response_filter.text)
    raise SystemExit("Audit filter request failed")

filtered_response = response_filter.json()
filtered_logs = filtered_response["items"]

for log in filtered_logs:
    if log["business_id"] != business_a_id:
        raise SystemExit("Filter returned another tenant")

    if log["action"] != "UPDATE":
        raise SystemExit("Action filter failed")

    if log["entity_type"] != "BUSINESS":
        raise SystemExit("Entity type filter failed")

print("AUDIT FILTERS: PASS")


# ------------------------------------------------------------
# Final result
# ------------------------------------------------------------
print("=" * 60)
print(" AUDIT LOG API SECURITY TEST: PASS")
print("=" * 60)
