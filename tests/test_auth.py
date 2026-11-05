def test_staff_login_success(client):
    response = client.post(
        "/auth/login",
        json={"email": "staff@couponengine.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["staff_email"] == "staff@couponengine.com"


def test_staff_login_wrong_password(client):
    response = client.post(
        "/auth/login",
        json={"email": "staff@couponengine.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_staff_login_nonexistent_user(client):
    response = client.post(
        "/auth/login",
        json={"email": "nonexistent@couponengine.com", "password": "Password123!"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_protected_routes_without_auth(client):
    res_list = client.get("/coupons")
    assert res_list.status_code == 401

    res_create = client.post(
        "/coupons",
        json={
            "code": "UNAUTHORIZED",
            "discount_percent": 10,
            "expiry_date": "2026-12-31T23:59:59Z",
            "usage_limit": 10,
        },
    )
    assert res_create.status_code == 401

    res_deactivate = client.patch("/coupons/TESTACTIVE/deactivate")
    assert res_deactivate.status_code == 401
