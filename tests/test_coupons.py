from datetime import datetime, timedelta, timezone


def test_create_and_list_coupons(client, auth_headers):
    # Create new coupon
    expiry = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
    create_res = client.post(
        "/coupons",
        headers=auth_headers,
        json={
            "code": "NEWCODE25",
            "discount_percent": 25.0,
            "expiry_date": expiry,
            "usage_limit": 50,
        },
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["code"] == "NEWCODE25"
    assert created_data["discount_percent"] == 25.0
    assert created_data["usage_limit"] == 50
    assert created_data["used_count"] == 0
    assert created_data["is_active"] is True

    # List coupons
    list_res = client.get("/coupons", headers=auth_headers)
    assert list_res.status_code == 200
    coupons = list_res.json()
    codes = [c["code"] for c in coupons]
    assert "NEWCODE25" in codes


def test_duplicate_coupon_creation(client, auth_headers):
    expiry = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
    res = client.post(
        "/coupons",
        headers=auth_headers,
        json={
            "code": "TESTACTIVE",
            "discount_percent": 20.0,
            "expiry_date": expiry,
            "usage_limit": 50,
        },
    )
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


def test_deactivate_coupon(client, auth_headers):
    res = client.patch("/coupons/TESTACTIVE/deactivate", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # Applying this deactivated coupon should now fail with 400
    apply_res = client.post("/coupons/TESTACTIVE/apply", json={"base_price": 100.0})
    assert apply_res.status_code == 400
    assert "deactivated" in apply_res.json()["detail"].lower()


def test_apply_coupon_success(client, auth_headers):
    # Create a fresh active coupon
    expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    client.post(
        "/coupons",
        headers=auth_headers,
        json={
            "code": "PROMO20",
            "discount_percent": 20.0,
            "expiry_date": expiry,
            "usage_limit": 10,
        },
    )

    # Apply against base price of ₹150.00
    apply_res = client.post("/coupons/PROMO20/apply", json={"base_price": 150.0})
    assert apply_res.status_code == 200
    data = apply_res.json()
    assert data["valid"] is True
    assert data["base_price"] == 150.0
    assert data["discount_percent"] == 20.0
    assert data["discounted_price"] == 120.0  # 150 - (20% of 150) = 120
    assert data["savings"] == 30.0


def test_apply_nonexistent_coupon(client):
    apply_res = client.post("/coupons/NONEXISTENT999/apply", json={"base_price": 100.0})
    assert apply_res.status_code == 404
    assert "does not exist" in apply_res.json()["detail"]


def test_apply_expired_coupon(client):
    apply_res = client.post("/coupons/TESTEXPIRED/apply", json={"base_price": 100.0})
    assert apply_res.status_code == 400
    assert "expired" in apply_res.json()["detail"].lower()


def test_apply_maxed_coupon(client):
    apply_res = client.post("/coupons/TESTMAXED/apply", json={"base_price": 100.0})
    assert apply_res.status_code == 400
    assert "usage limit" in apply_res.json()["detail"].lower()
