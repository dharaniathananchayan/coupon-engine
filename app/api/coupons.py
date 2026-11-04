from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.staff import Staff
from app.schemas.coupon import (
    CouponCreateRequest,
    CouponResponse,
    ApplyCouponRequest,
    ApplyCouponResponse,
)
from app.services.auth_service import get_current_staff
from app.services.coupon_service import (
    create_coupon,
    deactivate_coupon,
    list_coupons,
    apply_coupon,
)

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def api_create_coupon(
    payload: CouponCreateRequest,
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Staff only: Create a new coupon."""
    return create_coupon(db, payload)


@router.get("", response_model=List[CouponResponse])
def api_list_coupons(
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Staff only: List all coupons with their current used-counts."""
    return list_coupons(db)


@router.patch("/{code}/deactivate", response_model=CouponResponse)
def api_deactivate_coupon(
    code: str,
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Staff only: Deactivate a coupon by code."""
    return deactivate_coupon(db, code)


@router.post("/{code}/apply", response_model=ApplyCouponResponse)
def api_apply_coupon(
    code: str,
    payload: ApplyCouponRequest,
    db: Session = Depends(get_db),
):
    """
    Public: Validate and apply a coupon against a base price.
    
    Validation order:
    1. Code exists
    2. Is active
    3. Not past expiry date
    4. Under usage limit
    """
    return apply_coupon(db, raw_code=code, base_price=payload.base_price)
