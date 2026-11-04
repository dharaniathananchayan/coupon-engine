from datetime import datetime, timedelta, timezone
from app.database import engine, SessionLocal, Base
from app.models.staff import Staff
from app.models.coupon import Coupon
from app.models.redemption import Redemption
from app.services.auth_service import hash_password


def seed_database():
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 1. Seed Staff User
        staff_email = "staff@archintx.com"
        staff_password = "Password123!"
        existing_staff = db.query(Staff).filter(Staff.email == staff_email).first()

        if not existing_staff:
            print(f"Creating default staff user: {staff_email}")
            staff = Staff(
                email=staff_email,
                password_hash=hash_password(staff_password),
                created_at=now,
            )
            db.add(staff)
        else:
            print(f"Staff user {staff_email} already exists.")

        # 2. Seed Coupons
        seed_coupons_data = [
            {
                "code": "ACTIVE20",
                "discount_percent": 20.0,
                "expiry_date": now + timedelta(days=30),
                "usage_limit": 50,
                "used_count": 2,
                "is_active": True,
            },
            {
                "code": "EXPIRED10",
                "discount_percent": 10.0,
                "expiry_date": now - timedelta(days=7),
                "usage_limit": 100,
                "used_count": 5,
                "is_active": True,
            },
            {
                "code": "MAXED50",
                "discount_percent": 50.0,
                "expiry_date": now + timedelta(days=30),
                "usage_limit": 5,
                "used_count": 5,
                "is_active": True,
            },
            {
                "code": "DISABLED15",
                "discount_percent": 15.0,
                "expiry_date": now + timedelta(days=30),
                "usage_limit": 25,
                "used_count": 1,
                "is_active": False,
            },
            {
                "code": "MARKETINGINTX26",
                "discount_percent": 25.0,
                "expiry_date": now + timedelta(days=60),
                "usage_limit": 200,
                "used_count": 0,
                "is_active": True,
            },
        ]

        for item in seed_coupons_data:
            existing_coupon = db.query(Coupon).filter(Coupon.code == item["code"]).first()
            if not existing_coupon:
                print(f"Creating coupon: {item['code']} ({item['discount_percent']}%)")
                coupon = Coupon(
                    code=item["code"],
                    discount_percent=item["discount_percent"],
                    expiry_date=item["expiry_date"],
                    usage_limit=item["usage_limit"],
                    used_count=item["used_count"],
                    is_active=item["is_active"],
                    created_at=now,
                    updated_at=now,
                )
                db.add(coupon)
            else:
                print(f"Coupon {item['code']} already exists.")

        db.commit()
        print("Database seeding completed successfully!")
        print("\nTest Staff Credentials:")
        print(f"  Email:    {staff_email}")
        print(f"  Password: {staff_password}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
