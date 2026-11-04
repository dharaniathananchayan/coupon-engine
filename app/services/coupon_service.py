from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.coupon import Coupon
from app.models.redemption import Redemption
from app.schemas.coupon import CouponCreateRequest, ApplyCouponResponse


def normalize_code(code: str) -> str:
    return code.strip().upper()


def get_coupon_by_code(db: Session, code: str) -> Coupon | None:
    return db.query(Coupon).filter(Coupon.code == normalize_code(code)).first()


def list_coupons(db: Session) -> List[Coupon]:
    return db.query(Coupon).order_by(Coupon.created_at.desc()).all()


def create_coupon(db: Session, data: CouponCreateRequest) -> Coupon:
    code = normalize_code(data.code)
    existing = get_coupon_by_code(db, code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Coupon with code '{code}' already exists",
        )

    # Normalize naive datetime to UTC if needed
    expiry = data.expiry_date
    if expiry.tzinfo is not None:
        expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)

    coupon = Coupon(
        code=code,
        discount_percent=data.discount_percent,
        expiry_date=expiry,
        usage_limit=data.usage_limit,
        used_count=0,
        is_active=True,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


def deactivate_coupon(db: Session, raw_code: str) -> Coupon:
    code = normalize_code(raw_code)
    coupon = get_coupon_by_code(db, code)
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon with code '{code}' does not exist",
        )

    coupon.is_active = False
    coupon.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(coupon)
    return coupon


def apply_coupon(db: Session, raw_code: str, base_price: float) -> ApplyCouponResponse:
    """
    Validates and applies a coupon in strict priority order:
    1. Code exists
    2. Is active
    3. Not past expiry date
    4. Under its usage limit
    
    Guarantees concurrency safety via atomic conditional database update.
    """
    code = normalize_code(raw_code)

    # 1. Check code exists
    coupon = get_coupon_by_code(db, code)
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid coupon: Code '{code}' does not exist",
        )

    # 2. Check is active
    if not coupon.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inactive coupon: Code '{code}' has been deactivated",
        )

    # 3. Check not past expiry date
    now_utc = datetime.now(timezone.utc)
    expiry = coupon.expiry_date
    if expiry.tzinfo is None:
        expiry_comparison = expiry
        now_comparison = now_utc.replace(tzinfo=None)
    else:
        expiry_comparison = expiry
        now_comparison = now_utc

    if expiry_comparison <= now_comparison:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expired coupon: Code '{code}' expired on {coupon.expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        )

    # 4. Check under usage limit
    if coupon.used_count >= coupon.usage_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Usage limit reached: Code '{code}' has reached its maximum limit of {coupon.usage_limit} uses",
        )

    # Cache attributes needed for calculation before atomic query
    coupon_id = coupon.id
    coupon_code = coupon.code
    discount_percent = coupon.discount_percent
    db.expunge(coupon)

    # Atomic Execution Phase
    # Performs atomic increment directly in the database with strict WHERE guards
    db_now = now_utc.replace(tzinfo=None)
    stmt = (
        update(Coupon)
        .where(
            Coupon.id == coupon_id,
            Coupon.is_active.is_(True),
            Coupon.used_count < Coupon.usage_limit,
            Coupon.expiry_date > db_now,
        )
        .values(
            used_count=Coupon.used_count + 1,
            updated_at=db_now,
        )
    )

    result = db.execute(stmt)
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Usage limit reached: Code '{code}' could not be redeemed due to concurrent usage limit saturation",
        )

    # Calculate discounted price and savings
    discount_multiplier = 1.0 - (discount_percent / 100.0)
    discounted_price = round(base_price * discount_multiplier, 2)
    savings = round(base_price - discounted_price, 2)

    # Record redemption
    redemption = Redemption(
        coupon_id=coupon_id,
        base_price=base_price,
        discounted_price=discounted_price,
        redeemed_at=db_now,
    )
    db.add(redemption)
    db.commit()

    return ApplyCouponResponse(
        valid=True,
        code=coupon_code,
        base_price=base_price,
        discount_percent=discount_percent,
        discounted_price=discounted_price,
        savings=savings,
        message=f"Coupon '{coupon_code}' successfully applied! You saved ${savings:.2f} ({discount_percent}% off)",
    )
