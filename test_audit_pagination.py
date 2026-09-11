from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

from datetime import datetime

RUN_ID = datetime.now().strftime("%Y%m%d%H%M%S%f")

print("=" * 60)
print(" IMRAN BUSINESS OS")
print(" AUDIT LOG PAGINATION TEST")
print("=" * 60)

# ------------------------------------------------------------
# 1. Register isolated test business
# ------------------------------------------------------------
print("[1] Registering test business...")

response = client.post(
    "/api/v1/auth/register",
    json={
        "name": "Pagination Test Business " + RUN_ID,
        "business_name": "Pagination Test Business " + RUN_ID,
        "business_category": "retail",
        "country_code": "MW",
        "currency_code": "MWK",
        "timezone": "Africa/Blantyre",
        "language_code": "en",
        "email": "pagination_" + RUN_ID + "@example.com",
        "password": "PaginationTest123!",
    },
)

if response.status_code != 200:
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
    raise SystemExit("FAIL: registration")

data = response.json()

token = data.get("access_token")
if not token:
    raise SystemExit("FAIL: registration did not return access_token")

print("REGISTRATION: PASS")

headers = {
    "Authorization": f"Bearer {token}"
}

# ------------------------------------------------------------
# 2. Create several audit-producing actions
# ------------------------------------------------------------
print("[2] Creating audit records...")

for i in range(5):
    response = client.patch(
        "/api/v1/businesses/me",
        headers=headers,
        json={
            "name": f"Pagination Business {i}"
        },
    )

    if response.status_code != 200:
        print("STATUS:", response.status_code)
        print("BODY:", response.text)
        raise SystemExit("FAIL: business update")

print("AUDIT RECORD CREATION: PASS")

# ------------------------------------------------------------
# 3. Request first page
# ------------------------------------------------------------
print("[3] Testing first page...")

response = client.get(
    "/api/v1/audit-logs?limit=2&offset=0",
    headers=headers,
)

if response.status_code != 200:
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
    raise SystemExit("FAIL: first page request")

page_1 = response.json()

print("RESPONSE:", page_1)

required_fields = {
    "items",
    "limit",
    "offset",
    "total",
}

if not required_fields.issubset(page_1.keys()):
    raise SystemExit("FAIL: pagination fields missing")

if page_1["limit"] != 2:
    raise SystemExit("FAIL: limit metadata incorrect")

if page_1["offset"] != 0:
    raise SystemExit("FAIL: offset metadata incorrect")

if len(page_1["items"]) > 2:
    raise SystemExit("FAIL: returned more than requested limit")

if page_1["total"] < 5:
    raise SystemExit("FAIL: total count incorrect")

print("FIRST PAGE: PASS")
print("LIMIT:", page_1["limit"])
print("OFFSET:", page_1["offset"])
print("TOTAL:", page_1["total"])
print("ITEMS:", len(page_1["items"]))

# ------------------------------------------------------------
# 4. Request second page
# ------------------------------------------------------------
print("[4] Testing second page...")

response = client.get(
    "/api/v1/audit-logs?limit=2&offset=2",
    headers=headers,
)

if response.status_code != 200:
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
    raise SystemExit("FAIL: second page request")

page_2 = response.json()

if page_2["limit"] != 2:
    raise SystemExit("FAIL: second-page limit incorrect")

if page_2["offset"] != 2:
    raise SystemExit("FAIL: second-page offset incorrect")

if len(page_2["items"]) > 2:
    raise SystemExit("FAIL: second page returned too many records")

print("SECOND PAGE: PASS")

# ------------------------------------------------------------
# 5. Verify pages do not overlap
# ------------------------------------------------------------
print("[5] Checking page separation...")

ids_1 = {
    item["id"]
    for item in page_1["items"]
}

ids_2 = {
    item["id"]
    for item in page_2["items"]
}

if ids_1.intersection(ids_2):
    raise SystemExit("FAIL: pagination pages overlap")

print("PAGE SEPARATION: PASS")

# ------------------------------------------------------------
# Final
# ------------------------------------------------------------
print("=" * 60)
print(" AUDIT LOG PAGINATION TEST: PASS")
print("=" * 60)
