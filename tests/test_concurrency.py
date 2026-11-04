import concurrent.futures
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from tests.conftest import TestingSessionLocal
from app.models.coupon import Coupon
from app.models.redemption import Redemption


def test_concurrent_coupon_redemptions(client, auth_headers):
    """
    Stress test verifying that when multiple requests attempt to redeem the last available
    slots at the exact same moment, the database-level atomic lock prevents over-redemption.
    """
    # 1. Create a coupon with a strict usage limit of 5
    code = "RACECHECK5"
    expiry = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    create_res = client.post(
        "/coupons",
        headers=auth_headers,
        json={
            "code": code,
            "discount_percent": 10.0,
            "expiry_date": expiry,
            "usage_limit": 5,
        },
    )
    assert create_res.status_code == 201

    # 2. Fire 25 simultaneous requests
    concurrency_count = 25

    def attempt_redeem(req_idx: int):
        return client.post(f"/coupons/{code}/apply", json={"base_price": 100.0})

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(attempt_redeem, i) for i in range(concurrency_count)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # 3. Analyze responses
    success_responses = [r for r in results if r.status_code == 200]
    failure_responses = [r for r in results if r.status_code == 400]

    # Exactly 5 should succeed, remaining 20 must fail
    assert len(success_responses) == 5, f"Expected exactly 5 successes, but got {len(success_responses)}"
    assert len(failure_responses) == 20, f"Expected 20 rejected, but got {len(failure_responses)}"

    # 4. Check database directly
    db: Session = TestingSessionLocal()
    try:
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        assert coupon is not None
        assert coupon.used_count == 5, f"Coupon used_count must be 5, but was {coupon.used_count}"

        redemptions_count = db.query(Redemption).filter(Redemption.coupon_id == coupon.id).count()
        assert redemptions_count == 5, f"Expected 5 redemption records, but got {redemptions_count}"
    finally:
        db.close()
