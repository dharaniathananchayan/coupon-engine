from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CouponCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique coupon code")
    discount_percent: float = Field(..., gt=0, le=100, description="Discount percentage between 0 and 100")
    expiry_date: datetime = Field(..., description="Expiration timestamp (ISO 8601)")
    usage_limit: int = Field(..., gt=0, description="Maximum number of times coupon can be redeemed")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()


class CouponResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    discount_percent: float
    expiry_date: datetime
    usage_limit: int
    used_count: int
    is_active: bool
    created_at: datetime


class ApplyCouponRequest(BaseModel):
    base_price: float = Field(..., gt=0, description="Base order amount before discount")


class ApplyCouponResponse(BaseModel):
    valid: bool = True
    code: str
    base_price: float
    discount_percent: float
    discounted_price: float
    savings: float
    message: str = "Coupon applied successfully"
