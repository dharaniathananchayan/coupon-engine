from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Coupon(Base):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint("discount_percent > 0 AND discount_percent <= 100", name="chk_discount_percent"),
        CheckConstraint("usage_limit > 0", name="chk_usage_limit"),
        CheckConstraint("used_count >= 0 AND used_count <= usage_limit", name="chk_used_count"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, index=True, nullable=False)
    discount_percent = Column(Float, nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    usage_limit = Column(Integer, nullable=False)
    used_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    redemptions = relationship("Redemption", back_populates="coupon", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Coupon(code='{self.code}', discount={self.discount_percent}%, active={self.is_active})>"
